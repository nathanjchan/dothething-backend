import json
import logging
from google.oauth2 import id_token
from google.auth.transport import requests
import boto3
from botocore.exceptions import ClientError
import time
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dyn = boto3.resource('dynamodb')
table = dyn.Table('dothething-accounts')

def lambda_handler(event, context):
    logger.info('Request: %s', event)
    
    http_method = event.get('httpMethod')
    headers = event.get('headers')
    body = event.get('body')
    
    if http_method == 'POST':
        if body is not None:
            idToken = json.loads(body).get('idToken', '')
            if idToken != '':
                try:
                    # Specify the CLIENT_ID of the app that accesses the backend:
                    CLIENT_ID = '650326163788-pp25kvcqogpssfp108bln1pnhrunhju8.apps.googleusercontent.com'
                    idinfo = id_token.verify_oauth2_token(idToken, requests.Request(), CLIENT_ID)
                        
                    if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                        raise ValueError('Wrong issuer.')

                    # ID token is valid. Get the user's Google Account ID from the decoded token.
                    userid = idinfo['sub']
                    logger.info('User ID: %s', userid)

                    # add user to accounts table in dynamodb if not already there
                    try:
                        db_response = table.get_item(Key={'id': userid})
                        epoch = int(time.time() * 1000)
                        sessionId = uuid.uuid4().hex
                        if 'Item' not in db_response:
                            # new account
                            table.put_item(Item={'id': userid, 'sessionId': sessionId, 'timeOfCreation': epoch, 'timeOfLastLogin': epoch})
                        else:
                            # existing account
                            table.update_item(Key={'id': userid}, UpdateExpression='SET sessionId = :s, timeOfLastLogin = :t', ExpressionAttributeValues={':s': sessionId, ':t': epoch})
                    except ClientError as e:
                        logger.error(e.response['Error']['Message'])
                        return {
                            'statusCode': 500,
                            'body': json.dumps({'message': 'Internal database error'})
                        }
                    response = {
                        'statusCode': 200,
                        'body': json.dumps({
                            'message': 'Success',
                            'sessionId': sessionId
                        })
                    }
                except ValueError:
                    # Invalid token
                    response = {
                        'statusCode': 401,
                        'body': json.dumps({
                            'message': 'Invalid token'
                        })
                    }
            else:
                response = {
                    'statusCode': 400,
                    'body': json.dumps({
                        'message': 'Missing idToken'
                    })
                }
        else:
            response = {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'Missing body'
                })
            }
    else:
        response = {
            'statusCode': 405,
            'body': json.dumps({
                'message': 'Method not allowed'
            })
        }
    print("Response: ", response)
    return response
