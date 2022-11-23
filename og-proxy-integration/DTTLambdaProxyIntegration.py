import json
import logging
import boto3
import uuid
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from decimal import Decimal
import random
import base64

print("Loading function")

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
      if isinstance(obj, Decimal):
        return str(obj)
      return json.JSONEncoder.default(self, obj)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
dyn = boto3.resource('dynamodb')
videos_table = dyn.Table('dothethingvideos-metadata')
accounts_table = dyn.Table('dothething-accounts')

# given response["Items"], do all processing needed to get it ready for return
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

def lambda_handler(event, context):
    logger.info('Request: %s', event)
    
    http_method = event.get('httpMethod')
    headers = event.get('headers')
    
    if http_method == 'OPTIONS':
        response = {
            'statusCode': 200
        }

    elif 'password' not in headers or headers['password'] != 'ThisIsEpicPassword':
        response = {
            'statusCode': 401,
            'body': 'Invalid credentials.'
        }

    # DEFCON 0: get metadata for clips associated with given account
    elif http_method == 'GET' and 'session-id' in headers and 'batch-index' in headers:

        print("Entered DEFCON 0")
        session_id = headers['session-id']
        print("Session ID is", session_id)

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
                response = {
                    'statusCode': 401,
                    'body': 'Invalid session ID.'
                }
            else:
                account_id = response['Items'][0]['id']
                print("Account ID is", account_id)

                # query dothethingvideos-metadata to get all videos for this account
                try:
                    # query on secondary index accountId
                    response = videos_table.query(IndexName="accountId-index", KeyConditionExpression="accountId = :accountId", ExpressionAttributeValues={":accountId": account_id})
                except ClientError as err:
                    logger.error(
                        "Couldn't query for videos for account with ID %s. Here's why: %s: %s", account_id,
                        err.response['Error']['Code'], err.response['Error']['Message'])
                    raise
                else:
                    videos = processVideos(response['Items'], int(headers['batch-index']))
                    response = {
                        'statusCode': 200,
                        'body': json.dumps(videos, cls=DecimalEncoder)
                    }

    elif http_method == 'GET' and 'session-id' in headers:
        session_id = headers['session-id']
        print("Session ID is", session_id)
        try:
            response = accounts_table.query(IndexName="sessionId-index", KeyConditionExpression="sessionId = :sessionId", ExpressionAttributeValues={":sessionId": session_id})
        except ClientError as err:
            logger.error(
                "Couldn't query for account with session_id %s. Here's why: %s: %s", session_id,
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise
        else:
            if len(response['Items']) == 0:
                response = {
                    'statusCode': 401,
                    'body': 'Invalid session ID.'
                }
            else:
                response = {
                    'statusCode': 200,
                    'body': 'Valid session ID.'
                }
    
    # DEFCON 1.1: get metadata for existing thing, given code
    elif http_method == 'GET' and 'code' in headers and 'batch-index' in headers:
        
        print("Entered DEFCON 1.1")
        code = headers['code']

        # use DynamoDB to get all "id"s with "code" and sort by "timeOfCreation" in ascending order
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
            videos = processVideos(response['Items'], int(headers['batch-index']))
            response = {
                'statusCode': 200,
                'body': json.dumps(videos, cls=DecimalEncoder)
            }

    elif http_method == 'GET' and 'code' in headers:
        code = headers['code']
        message = "Bruh check out this domino cascade I made. Use code {} and get the app https://thedominoapp.com".format(code)
        response = {
            'statusCode': 200,
            'body': json.dumps(message)
        }
            
    # DEFCON 1.2: get presigned URL given id
    elif http_method == 'GET' and 'id' in headers:
        
        print("Entered DEFCON 1.2")
        id = headers['id']
        presigned_url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': 'dothethingvideos',
                'Key': id
            }
        )
        response = {
            'statusCode': 200,
            'body': presigned_url
        }
        
    # DEFCON 2.1: upload to existing thing
    elif http_method == 'PUT' and 'code' in headers and 'file-extension' in headers and 'session-id' in headers:
        
        print("Entered DEFCON 2.1")
        code = headers['code']
        session_id = headers['session-id']

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
                response = {
                    'statusCode': 401,
                    'body': 'Invalid session ID.'
                }
            else:
                account_id = response['Items'][0]['id']
                # check if a video exists with this code (primary key)
                try:
                    response = videos_table.query(KeyConditionExpression=Key('code').eq(code))
                except ClientError as err:
                    logger.error(
                        "Couldn't query for videos with code %s and account_id %s. Here's why: %s: %s", code, account_id,
                        err.response['Error']['Code'], err.response['Error']['Message'])
                    raise
                else:
                    file_extension = headers['file-extension'].strip('.').lower()
                    key = '{}-{}-{}.{}'.format(code, uuid.uuid4().hex, session_id, file_extension)
                    presigned_url = s3.generate_presigned_url(
                        ClientMethod='put_object',
                        Params={
                            'Bucket': 'dothethingvideos',
                            'Key': key
                        }
                    )
                    response = {
                        'statusCode': 200,
                        'body': presigned_url
                    }
        
    # DEFCON 3.1: create new thing
    elif http_method == 'POST' and 'file-extension' in headers and 'session-id' in headers:
        
        def generateCode():
            code = ''.join(random.choice("123456789abcdefABCDEF") for _ in range(8))
            try:
                response = videos_table.query(KeyConditionExpression=Key('code').eq(code))
            except ClientError as err:
                logger.error(
                    "Couldn't query for videos with code %s. Here's why: %s: %s", code,
                    err.response['Error']['Code'], err.response['Error']['Message'])
                raise
            else:
                if len(response["Items"]) == 0:
                    return code
                else:
                    return generateCode()
        
        print("Entered DEFCON 3.1")
        file_extension = headers['file-extension'].strip('.').lower()
        session_id = headers['session-id']
        code = generateCode()
        key = '{}-{}-{}.{}'.format(code, uuid.uuid4().hex, session_id, file_extension)
        presigned_url = s3.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': 'dothethingvideos',
                'Key': key
            }
        )
        response = {
            'statusCode': 200,
            'body': presigned_url
        }
        
    else:
        response = {
            'statusCode': 400,
            'body': 'Must specify code/file extension/session ID/batch index.'
        }
    
    response['headers'] = {
        "Access-Control-Allow-Headers": "code,password,batch-index",
        "Access-Control-Allow-Origin": "*"
    }
    return response
