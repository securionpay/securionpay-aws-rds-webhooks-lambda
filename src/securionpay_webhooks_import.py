import base64
import json
import logging
import os
import re
import pymysql
from collections import OrderedDict
from datetime import datetime

DATABASE_HOST = os.environ.get('database_host')
DATABASE_NAME = os.environ.get('database_name')
DATABASE_USER = os.environ.get('database_user')
DATABASE_PASSWORD = os.environ.get('database_password')
TIMESTAMP_FIELDS = [
    '*.created', '*.updated',
    'card_mcc6012Data.birthDate', 'credit_mcc6012Data.birthDate',
    'subscription.start', 'subscription.currentPeriodStart', 'subscription.currentPeriodEnd', 'subscription.canceledAt',
    'subscription.endedAt', 'subscription.trialStart', 'subscription.trialEnd',
]

log = logging.getLogger()
log.setLevel(logging.INFO)

connection = pymysql.connect(host=DATABASE_HOST, db=DATABASE_NAME, user=DATABASE_USER, password=DATABASE_PASSWORD,
                             charset='utf8', cursorclass=pymysql.cursors.DictCursor)


def lambda_handler(event, context):
    with Database(connection) as database:
        webhook_importer = WebhookImporter(database)

        for record in event['Records']:
            webhook_json = base64.b64decode(record['kinesis']['data']).decode('utf-8')
            log.info("Processing webhook: %s" % webhook_json)

            webhook = json.loads(webhook_json, object_pairs_hook=OrderedDict)

            webhook_importer.import_object(webhook['data'])

    return 'Done.'


class WebhookImporter:
    def __init__(self, database):
        self.database = database

    def import_object(self, object):
        id = object['id']
        table = object['objectType']

        self.database.ensure_table(table, {'id': str})

        self.database.insert_row(table, self.__build_row(table, object))

        return id

    def import_metadata(self, object, metadata):
        id = object['id']
        type = object['objectType']
        table = type + '_metadata'

        self.database.ensure_table(table, {type: str, 'key': str})
        self.database.ensure_column(table, 'value', str, after_column='key')

        for key, value in metadata.items():
            self.database.insert_row(table, {type: id, 'key': key, 'value': value})

    def import_list(self, object, key, list):
        id = object['id']
        type = object['objectType']

        table = type + '_' + key
        self.database.ensure_table(table, {type: str, 'index': int})

        for index, value in enumerate(list):
            row = {type: id, 'index': index}

            if self.__is_standalone_object(value):
                row[value['objectType']] = self.import_object(value)
            elif self.__is_object(value):
                row.update(value)
            else:
                row['value'] = value

            self.database.insert_row(table, self.__build_row(table, row))

        self.database.delete_old_list_rows(table, type, id, len(list))

    def __build_row(self, table, object, prefix='', after_column='id'):
        row = OrderedDict()
        for key, value in object.items():
            column = prefix + key

            if value is None:
                continue
            elif key == 'metadata':
                self.import_metadata(object, value)
                continue
            elif key == 'objectType':
                continue
            elif self.__is_standalone_object(value):
                value = self.import_object(value)
            elif self.__is_object(value):
                row.update(self.__build_row(table, value, column + '_', after_column))
                after_column = next(reversed(row))
                continue
            elif type(value) is list:
                self.import_list(object, key, value)
                continue
            elif type(value) is bool:
                value = 1 if value else 0
            elif self.__is_timestamp_field(table, key):
                value = datetime.utcfromtimestamp(value)

            self.database.ensure_column(table, column, type(value), after_column)
            row[column] = value
            after_column = column

        return row

    def __is_standalone_object(self, value):
        return self.__is_object(value) \
               and 'id' in value \
               and 'objectType' in value

    def __is_object(self, value):
        return type(value) is dict or type(value) is OrderedDict

    def __is_timestamp_field(self, table, key):
        return ('*.%s' % key) in TIMESTAMP_FIELDS \
               or ('%s.%s' % (table, key)) in TIMESTAMP_FIELDS


class Database:
    def __init__(self, connection):
        self.connection = connection
        self.log = logging.getLogger('database')
        self.tables = {}

    def __enter__(self):
        self.cursor = self.connection.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()

        if exc_val is None:
            self.connection.commit()
        else:
            self.connection.rollback()

        self.cursor = None

    def ensure_table(self, table, primary_keys):
        if table in self.tables:
            return

        if self.__execute("SHOW TABLES LIKE '%s'" % self.__escape_name(table)) > 0:
            self.tables[table] = [row['Field'] for row in
                                  self.__query("SHOW COLUMNS FROM %s" % self.__quote_name(table))]
            return

        sql = "CREATE TABLE %s (" % self.__quote_name(table)
        for column, type in primary_keys.items():
            sql += "%s %s NOT NULL, " % (self.__quote_name(column), self.__get_sql_type(table, column, type))

        sql += "PRIMARY KEY (%s)" % self.__quote_list_of_names(primary_keys.keys())
        sql += ") CHARSET='utf8' COLLATE='utf8_general_ci' ENGINE=InnoDB "

        self.__execute(sql)
        self.tables[table] = [column for column in primary_keys.keys()]

    def ensure_column(self, table, column, type, after_column):
        if column in self.tables[table]:
            return

        sql_type = self.__get_sql_type(table, column, type)

        self.__execute("ALTER TABLE `%s` "
                       "ADD COLUMN `%s` %s NULL AFTER `%s`"
                       % (table, column, sql_type, after_column))

        self.tables[table].append(column)

    def __get_sql_type(self, table, column, type):
        if type is str:
            return 'VARCHAR(255)'
        elif type is int:
            return 'BIGINT'
        elif type is bool:
            return 'BIT(1)'
        elif type is datetime:
            return 'DATETIME(3)'
        else:
            raise Exception('Unsupported column type: table=%s, column=%s, type=%s' % (table, column, type))

    def insert_row(self, table, row):
        columns_sql = self.__quote_list_of_names(row.keys())
        values_sql = ', '.join(['%s' for key in row.keys()])
        values = [value for value in row.values()]

        self.__execute("REPLACE INTO %s (%s) VALUES (%s)" % (self.__quote_name(table), columns_sql, values_sql), values)

    def delete_old_list_rows(self, table, id, value, size):
        sql = "DELETE FROM %s WHERE %s = %s AND `index` >= %s" % (
            self.__quote_name(table), self.__quote_name(id), '%s', '%s')
        self.__execute(sql, (value, size))

    def commit(self):
        self.connection.commit()

    def __execute(self, sql, args=None):
        self.log.info(self.cursor.mogrify(sql, args))
        return self.cursor.execute(sql, args)

    def __query(self, sql):
        self.__execute(sql)
        return self.cursor.fetchall()

    def __quote_list_of_names(self, names):
        return ', '.join([self.__quote_name(column) for column in names])

    def __quote_name(self, name):
        return '`' + self.__escape_name(name) + '`'

    def __escape_name(self, name):
        return re.sub(r'[^a-zA-Z0-9_]+', '', name)
