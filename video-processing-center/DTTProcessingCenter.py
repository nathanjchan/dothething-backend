import json
import urllib.parse
import boto3
import os
import logging
from botocore.exceptions import ClientError
import time

print("Loading function")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
dyn = boto3.resource('dynamodb')
videos_table = dyn.Table('dothethingvideos-metadata')
accounts_table = dyn.Table('dothething-accounts')

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent = 2))
    
    # get the object from the event
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = urllib.parse.unquote_plus(event["Records"][0]["s3"]["object"]["key"], encoding="utf-8")
    
    # parse code from key
    key_split = key.split("-")
    code = key_split[0]
    print("Code is:", code)
    
    # parse session_id from key
    session_id = key_split[2].split(".")[0]
    print("Session ID is", session_id)

    try:
        # download video from S3
        response = s3.get_object(Bucket=bucket, Key=key)

        # write video to /tmp
        os.chdir("/tmp")
        tmp_file = key
        with open(tmp_file, "wb") as f:
            f.write(response["Body"].read())

        # get thumbnail of video
        thumbnail = "".join([key, ".jpg"])
        os.system("ffmpeg -i {} -ss 00:00:01.000 -vframes 1 {}".format(key, thumbnail))

        # upload thumbnail to S3
        s3.upload_file(thumbnail, "dothethingthumbnails", thumbnail)

    except Exception as e:
        print(e)
        print("Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.".format(key, bucket))
        raise e
    
    # query dothething-accounts to get account_id of the account with session_id
    try:
        # query on secondary index session_id
        response = accounts_table.query(IndexName="sessionId-index", KeyConditionExpression="sessionId = :sessionId", ExpressionAttributeValues={":sessionId": session_id})
    except ClientError as err:
        logger.error(
            "Couldn't query for account with session_id %s. Here's why: %s: %s", session_id,
            err.response['Error']['Code'], err.response['Error']['Message'])
        raise
    else:
        if len(response['Items']) == 0:
            print("No account found with session ID", session_id)
            return
            
        account_id = response['Items'][0]['id']
        print("Account ID is", account_id)

        # get epoch time in milliseconds
        epoch = int(time.time() * 1000)
        print("Epoch is: " + str(epoch))

        # add this object's metadata to DynamoDB (dothethingvideos-metadata)
        try:
            videos_table.put_item(
                Item={
                    'code': code,
                    'id': key,
                    'timeOfCreation': epoch,
                    'accountId': account_id
                }
            )
        except ClientError as err:
            logger.error(
                "Couldn't add video with id %s to table %s. Here's why: %s: %s",
                key, videos_table.name,
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise
            