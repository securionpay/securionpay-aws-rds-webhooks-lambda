# SecurionPay AWS - RDS Webhooks Lambda

This lambda can be used to synchronize data from your SecurionPay account to a MySQL database server.

Once the data are in MySQL database it is possible to:
- easily run custom SQL queries to answer common business questions (i.e. what is my current chargeback ratio)
- use business intelligence tools (like [AWS QuickSight](https://quicksight.aws/)) to analyze and visualize your data
- and much more ...   

## Setup instruction

### 1. Login to you Amazon AWS web console

- Go to [Amazon Web Services Sign-In](https://console.aws.amazon.com)

### 2. Create new Kinesis stream

- Click "Services" button in top left corner and select "Kinesis" (under Analytics group) 
- Select "Data Streams" from left menu
- Click "Create Kinesis stream"
- Fill "Kinesis stream name" with some descriptive name for your new stream (for example "SecurionPay-webhooks")
- Fill "Number of shards" with "1" (this can be always increased later)
- Click "Create Kinesis stream"

### 3. Create IAM Policy that allows SecurionPay to write to your Kinesis stream

- Click "Services" button in top left corner and select "IAM" (under Security, Identity & Compliance group)
- Select "Policies" from left menu
- Click "Create policy"
- Fill new policy by using visual editor:
  - Service: "Kinesis"
  - Actions: "PutRecord" and "PutRecords" (found under "Write" section)
  - Resources: paste "Stream ARN" of Kinesis stream created in step 2 (it should look like this: "arn:aws:kinesis:eu-west-1:888888888888:stream/SecurionPay-webhooks")
- Click "Review Policy"
- Fill "Name" with some descriptive name for your new policy (for example "SecurionPay-webhooks-access")
- Click "Create Policy"

### 4. Create IAM Role that will be used by SecurionPay

- Click "Services" button in top left corner and select "IAM" (under Security, Identity & Compliance group)
- Select "Roles" from left menu
- Click "Create role"
- Change "Select type of trusted entity" to "Another AWS account"
- Fill "Account ID" with "241240850447" (this is SecurionPay's AWS account used to send webhooks)
- Do not select any additional options
- Click "Next: Permissions"
- Search for IAM Policy created in step 3 and select it
- Click "Next: Review"
- Fill "Name" with some descriptive name for you new role (for example "SecurionPay-webhooks")
- Click "Create role" 

### 5. Create Lambda that will import webhooks to MySQL database

- Click "Services" button in top left corner and select "Lambda" (under Compute group)
- Select "Functions" from left menu
- Click "Create function"
- Select "Author from scratch"
- Fill "Name" with some descriptive name for your new Lambda (for example "SecurionPay-webhooks-import")
- Select "Runtime" as "Python 3.6"
- Change "Role" to "Create a custom role" (and create new role in new popup window)
- Click "Create function"
- In "configuration" tab, under "Add triggers":
  - Click "Kinesis"
  - Fill "Kinesis stream" with ARN of Kinesis stream created in step 2 (it should look like this: "arn:aws:kinesis:eu-west-1:888888888888:stream/SecurionPay-webhooks")
  - Leave other options with their default values
  - Click "Add"
  - Click "Save" (in upper right corner)
  - Click on your lambda name to return to main view
  - Add permissions required to use Kinesis stream to role used by your Lambda (permissions: GetRecords, GetShardIterator, DescribeStream, and ListStreams)
- In "Function code" tab:
  - Change "Code entry type" to "Upload a .ZIP file"
  - Click "Upload" under "Function package" label
  - Upload ZIP file downloaded from [releases page](https://github.com/securionpay/securionpay-aws-rds-webhooks-lambda/releases)
  - Change "Handler" to "securionpay_webhooks_import.lambda_handler"
  - Click "Save" (in upper right corner)
- In "Environment variables" tab add following keys:
  - "database_host" - IP or hostname of you MySQL server (for example "securionpay-webhooks.aaa.eu-west-1.rds.amazonaws.com")
  - "database_name" - name of database scheme (for example "securionpay-webhooks")
  - "database_user" - username that will be used
  - "database_password" - password for provided user
  - Click "Save" (in upper right corner)

### 6. Configure SecurionPay to send webhooks to your Kinesis stream

- Login to your [SecurionPay account](https://securionpay.com/login)
- Click you account name (in upper right corner) and select "Account settings"
- Select "Webhooks" tab
- Click "Add Endpoint"
- Select "AWS Kinesis" type
- Fill "Stream ARN" with ARN of Kinesis stream created in step 2 (it should look like this: "arn:aws:kinesis:eu-west-1:888888888888:stream/SecurionPay-webhooks")
- Fill "Role ARN" with ARN of Role created in step 4 (it should look like this: "arn:aws:iam::888888888888:role/SecurionPay-webhooks")
- Click "Create Endpoint"

### 7. Test your configuration

- Create new test charge in SecurionPay
- Check if charge data correctly propagated to your MySQL database
