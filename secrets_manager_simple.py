import boto3
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
import json
from typing import Optional, Dict, Any

def get_secret(secret_name: str = "LF_TOKEN", region_name: str = "eu-north-1") -> Optional[str]:
    
    print(f"Starting secret retrieval: {secret_name} in {region_name}")
    
    try:
        session = boto3.session.Session()
        
        print("Creating Secrets Manager client")
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
        
        print("Attempting to retrieve secret value")
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        
        secret = get_secret_value_response['SecretString']
        
        print(f"Secret retrieved successfully: {len(secret) if secret else 0} characters")
        
        return secret
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"ERROR: AWS ClientError - {error_code}: {e}")
        
        if error_code == 'DecryptionFailureException':
            print("ERROR: Secrets Manager can't decrypt the protected secret text using the provided KMS key")
        elif error_code == 'InternalServiceErrorException':
            print("ERROR: An error occurred on the server side")
        elif error_code == 'InvalidParameterException':
            print("ERROR: You provided an invalid value for a parameter")
        elif error_code == 'InvalidRequestException':
            print("ERROR: You provided a parameter value that is not valid for the current state")
        elif error_code == 'ResourceNotFoundException':
            print(f"ERROR: The requested secret {secret_name} was not found")
        
        return None
        
    except NoCredentialsError as e:
        print(f"ERROR: AWS credentials not found: {e}")
        return None
        
    except BotoCoreError as e:
        print(f"ERROR: BotoCore error occurred: {e}")
        return None
        
    except Exception as e:
        print(f"ERROR: Unexpected error occurred: {e}")
        return None

def get_secret_dict(secret_name: str, region_name: str = "eu-north-1") -> Optional[Dict[str, Any]]:
    
    print(f"Retrieving secret as JSON dictionary: {secret_name}")
    
    secret_string = get_secret(secret_name, region_name)
    
    if not secret_string:
        print("ERROR: No secret string retrieved")
        return None
    
    try:
        secret_dict = json.loads(secret_string)
        print(f"Secret parsed as JSON successfully: {len(secret_dict)} keys")
        return secret_dict
        
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse secret as JSON: {e}")
        return None
        
    except Exception as e:
        print(f"ERROR: Unexpected error parsing secret: {e}")
        return None 