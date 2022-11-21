import json
import logging
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dyn = boto3.resource('dynamodb')
videos_table = dyn.Table('dothethingvideos-metadata')
accounts_table = dyn.Table('dothething-accounts')

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

def lambda_handler(event, context):
    logger.info("Request: %s", event)

    http_method = event.get('httpMethod')
    headers = event.get('headers')

    if "password" not in headers or headers["password"] != "ThisIsEpicPassword":
        response = {
            "statusCode": 401,
            "body": json.dumps("Invalid credentials.")
        }
    
    elif http_method == "GET" and "session-id" in headers:
        account_id = getAccountIdFromSessionId(headers["session-id"])
        codes = getCodesForAccount(account_id)
        codes = list(codes)
        response = {
            "statusCode": 200,
            "body": json.dumps(codes)
        }

    logger.info("Response: %s", response)
    return response
