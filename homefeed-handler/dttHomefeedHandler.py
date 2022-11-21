import json
import logging
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
import base64
from decimal import Decimal
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
dyn = boto3.resource('dynamodb')
videos_table = dyn.Table('dothethingvideos-metadata')
accounts_table = dyn.Table('dothething-accounts')

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
      if isinstance(obj, Decimal):
        return str(obj)
      return json.JSONEncoder.default(self, obj)

def getAccountIdFromSessionId(session_id: str) -> str:
    logger.info("Session ID is %s", session_id)
    try:
        response = accounts_table.query(IndexName="sessionId-index", KeyConditionExpression="sessionId = :sessionId", ExpressionAttributeValues={":sessionId": session_id})
    except ClientError as err:
        logger.error(
            "Couldn't query for account with session_id %s. Here's why: %s: %s", session_id,
            err.response['Error']['Code'], err.response['Error']['Message'])
        raise
    else:
        account_id = response["Items"][0]["id"]
        logger.info("Account ID is %s", account_id)
        return account_id

def getCodesForAccount(account_id: str) -> set:
    try:
        response = videos_table.query(IndexName="accountId-index", KeyConditionExpression="accountId = :accountId", ExpressionAttributeValues={":accountId": account_id})
    except ClientError as err:
        logger.error(
            "Couldn't query for clips with account_id %s. Here's why: %s: %s", account_id,
            err.response['Error']['Code'], err.response['Error']['Message'])
        raise
    else:
        codes = set()
        for item in response["Items"]:
            codes.add(item["code"])
        logger.info("Codes are %s", codes)
        return codes

def getVideosForCode(code: str) -> dict:
    try:
        response = videos_table.query(
            KeyConditionExpression=Key('code').eq(code),
            ScanIndexForward=True
        )
    except ClientError as err:
        logger.error(
            "Couldn't query for videos with code %s. Here's why: %s: %s", code,
            err.response['Error']['Code'], err.response['Error']['Message'])
        raise
    else:
        return response["Items"]

def processVideos(videos: dict, batch_index: int) -> dict:
    videos.sort(key=lambda x: x['timeOfCreation'], reverse=True)
    start_index = batch_index * 33
    end_index = start_index + 33
    videos = videos[start_index:end_index]
    print("Videos are", videos)

    for video in videos:
        del video['accountId']
        try:
            thumbnailBytes = s3.get_object(Bucket='dothethingthumbnails', Key=video['id'] + '.jpg')['Body'].read()
        except:
            thumbnailBytes = s3.get_object(Bucket='dothethingthumbnails', Key="obama.jpg")['Body'].read()
        video['thumbnailBase64'] = base64.b64encode(thumbnailBytes).decode('utf-8')
    return videos

def setInteractions(account_id: str, interactions: int) -> None:
    try:
        response = accounts_table.update_item(
            Key={'id': account_id},
            UpdateExpression="set interactions = :interactions",
            ExpressionAttributeValues={":interactions": interactions},
            ReturnValues="UPDATED_NEW"
        )
    except ClientError as err:
        logger.error(
            "Couldn't update interactions for account_id %s. Here's why: %s: %s", account_id,
            err.response['Error']['Code'], err.response['Error']['Message'])
        raise
    else:
        logger.info("Successfully updated interactions for account_id %s", account_id)

def getInteractions(account_id: str) -> int:
    try:
        response = accounts_table.query(
            KeyConditionExpression=Key('id').eq(account_id)
        )
    except ClientError as err:
        logger.error(
            "Couldn't query for interactions with account_id %s. Here's why: %s: %s", account_id,
            err.response['Error']['Code'], err.response['Error']['Message'])
        raise
    else:
        return response["Items"][0]["interactions"]

def lambda_handler(event, context):
    logger.info("Request: %s", event)

    http_method = event.get('httpMethod')
    headers = event.get('headers')

    if "password" not in headers or headers["password"] != "ThisIsEpicPassword":
        response = {
            "statusCode": 401,
            "body": json.dumps("Invalid credentials.")
        }
    
    elif http_method == "GET" and "session-id" in headers and "batch-index" in headers:
        account_id = getAccountIdFromSessionId(headers["session-id"])
        codes = getCodesForAccount(account_id)
        codes = list(codes)
        all_videos = []
        for code in codes:
            videos = getVideosForCode(code)
            all_videos.extend(videos)
        setInteractions(account_id, len(all_videos))
        all_videos = processVideos(all_videos, int(headers['batch-index']))
        response = {
            "statusCode": 200,
            "body": json.dumps(all_videos, cls=DecimalEncoder)
        }

    elif http_method == "GET" and "session-id" in headers:
        account_id = getAccountIdFromSessionId(headers["session-id"])
        num_interactions = getInteractions(account_id)
        logger.info("Interaction number is %s", num_interactions)
        response = {
            "statusCode": 200,
            "body": json.dumps(str(num_interactions))
        }

    else:
        response = {
            "statusCode": 400,
            "body": json.dumps("Invalid request.")
        }

    logger.info("Response: %s", response)
    return response
