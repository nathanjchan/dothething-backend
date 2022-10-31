import json
import logging
from google.oauth2 import id_token
from google.auth.transport import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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
                    idinfo = id_token.verify_oauth2_token(idToken, requests.Request(), 'CLIENT_ID')
                        
                    if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                        raise ValueError('Wrong issuer.')

                    # ID token is valid. Get the user's Google Account ID from the decoded token.
                    userid = idinfo['sub']
                    logger.info('User ID: %s', userid)
                    return {
                        'statusCode': 200,
                        'body': json.dumps({
                            'message': 'Success'
                        })
                    }
                except ValueError:
                    # Invalid token
                    return {
                        'statusCode': 401,
                        'body': json.dumps({
                            'message': 'Invalid token'
                        })
                    }
            else:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'message': 'Missing idToken'
                    })
                }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'Missing body'
                })
            }
    else:
        return {
            'statusCode': 405,
            'body': json.dumps({
                'message': 'Method not allowed'
            })
        }
        