# SecurionPay AWS - RDS Webhooks Lambda

This Lambda can be used to synchronize data from your SecurionPay account to the MySQL database server.

Once the data is imported into MySQL database, it is possible to:
- easily run custom SQL queries to answer common business questions (i.e. What is my current chargeback ratio?)
- use business intelligence tools (like [AWS QuickSight](https://quicksight.aws/)) to analyze and visualize your data
- and much more...  


## High level overview

Here’s the most common setup for using Lambda from this repository:
- Transactions (and other objects like customer, chargebacks, ...) are created in SecurionPay during regular payment processing
- SecurionPay is configured to send webhook events to AWS Kinesis stream
- Lambda (of which code is provided in this repository) is configured to pull data from AWS Kinesis stream and save it to MySQL database server (hosted via AWS RDS)
- The MySQL server contains copy of all data from SecurionPay (with near real-time synchronization)


## Setup instruction

### 1. Log in to your Amazon Web Services web console

- Go to [Amazon Web Services Sign-In](https://console.aws.amazon.com)
- Log in to your account

### 2. Create new Kinesis stream

- Click "Services" button in the top left corner and select "Kinesis" (under Analytics group)
- Select "Data Streams" from the left-hand menu
- Click "Create Kinesis stream"
- Fill in "Kinesis stream name" with a descriptive name for your new stream (for example, "SecurionPay-webhooks")
- Fill in "Number of shards" with "1" (1 is a good starting point and this can be increased later)
- Click "Create Kinesis stream"

### 3. Create IAM Security Policy that allows writing to your Kinesis stream

- Click "Services" button in the top left corner and select "IAM" (under Security, Identity & Compliance group)
- Select "Policies" from the left-hand menu
- Click "Create policy"
- Configure new policy using visual editor:
 - Service: select "Kinesis"
 - Actions: select "PutRecord" and "PutRecords" (under "Write" section)
 - Resources: paste "Stream ARN" of Kinesis stream created in step 2 (it should look like this: "arn:aws:kinesis:eu-west-1:888888888888:stream/SecurionPay-webhooks")
- Click "Review Policy"
- Fill in "Name" with a descriptive name for your new policy (for example "SecurionPay-webhooks-kinesis-put-records")
- Click "Create Policy"

### 4. Create IAM Role that allows SecurionPay to access your Kinesis stream

- Click "Services" button in the top left corner and select "IAM" (under Security, Identity & Compliance group)
- Select "Roles" from the left-hand menu
- Click "Create role"
- Change "Type of trusted entity" to "Another AWS account"
- Fill in "Account ID" with "**241240850447**" (this is SecurionPay's AWS account used to send webhooks)
- Click "Next: Permissions"
- Search for IAM Policy created in step 3 and select it
- Click "Next: Review"
- Fill in "Name" with a descriptive name for you new role (for example, "SecurionPay-webhooks-access")
- Click "Create role"

### 5. Create RDS that will be used to store processed data

- Click "Services" button in the top left corner and select "RDS" (under Database group)
- Select "Instances" from the left-hand menu
- Click "Launch DB instance"
- Select "Amazon Aurora" engine with "MySQL compatible" edition (or any other MySQL compatible database engine)
- Click "Next"
- Configure the instance based on your needs
- Create database instance

### 6. Create IAM Role that will be used in Lambda

- Click "Services" button in the top left corner and select "IAM" (under Security, Identity & Compliance group)
- Select "Roles" from the left-hand menu
- Click "Create role"
- Select "Lambda" as "the service that will use this role"
- Click "Next: Permissions"
- Select following predefined policies: "AWSLambdaKinesisExecutionRole" and "AWSLambdaVPCAccessExecutionRole"
- Click "Next: Review"
- Fill in "Name" with a descriptive name for your new role (for example "SecurionPay-webhooks-lambda")
- Click "Create role"

### 7. Create Lambda that will import data from Kinesis stream into MySQL database

- Click "Services" button in the top left corner and select "Lambda" (under Compute group)
- Select "Functions" from left-hand menu
- Click "Create function"
- Select "Author from scratch"
- Fill in the "Name" field with a descriptive name for your new Lambda (for example, "SecurionPay-webhooks")
- Select "Runtime" as "Python 3.6"
- Change "Existing role" to the Role created in step 6 (it should look like this: "arn:aws:iam::888888888888:role/SecurionPay-webhooks-lambda")
- Click "Create function"
- In "configuration" tab, under "Add triggers":
 - Click "Kinesis"
 - Fill in "Kinesis stream" with ARN of Kinesis stream created in step 2 (it should look like this: "arn:aws:kinesis:eu-west-1:888888888888:stream/SecurionPay-webhooks")
 - Click "Add"
 - Click "Save" (in the upper-right corner)
 - Click your Lambda name to return to the main view
- In the "Function code" tab:
 - Change "Code entry type" to "Upload a .ZIP file"
 - Click "Upload" under "Function package" label
 - Upload ZIP file downloaded from [releases page](https://github.com/securionpay/securionpay-aws-rds-webhooks-lambda/releases)
 - Change "Handler" to "securionpay_webhooks_import.lambda_handler"
 - Click "Save" (in the upper-right corner)
- In "Environment variables" tab add following keys:
 - "database_host" - endpoint of your RDS instance (for example "securionpay-webhooks.aaa.eu-west-1.rds.amazonaws.com")
 - "database_name" - name of database schema (for example "securionpay")
 - "database_user" - username that will be used to access RDS
 - "database_password" - password that will be used to access RDS
 - Click "Save" (in the top right corner)
- Test your Lambda configuration
 - From the drop down near the "Test" button (in the upper-right corner), select "Configure test events"
 - Select "Create new test event"
 - Add following test data:
   ```
   {
     "Records": [{
         "kinesis": {
           "data": "ew0KICAiZGF0YSI6IHsNCiAgICAiaWQiOiAidGVzdC0xIiwNCiAgICAib2JqZWN0VHlwZSI6ICJ0ZXN0Ig0KICB9DQp9"
         }
     }]
   }
   ```
 - Click "Create"
 - Execute created test

### 8. Configure SecurionPay account to send webhooks to your Kinesis stream

- Log in to your [SecurionPay account](https://securionpay.com/login)
- Click your account name (in the right corner) and select "Account settings"
- Select "Webhooks" tab
- Click "Add Endpoint"
- Select "AWS Kinesis" type
- Fill "Stream ARN" with ARN of Kinesis stream created in step 2 (it should look like this: "arn:aws:kinesis:eu-west-1:888888888888:stream/SecurionPay-webhooks")
- Fill "Role ARN" with ARN of Role created in step 4 (it should look like this: "arn:aws:iam::888888888888:role/SecurionPay-webhooks-access")
- Click "Create Endpoint"

### 9. Test your configuration

- To test your configuration, enable "Test Mode" from SecurionPay dashboard
- Go to "Charges" tab and create new test charge by clicking "Add charge"
- Go to "Events" tab and ensure that newly created events were successfully dispatched to your Kinesis stream
- Log in to your database and check whether the charge data was successfully synchronized