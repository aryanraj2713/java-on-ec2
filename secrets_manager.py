import boto3
import logfire
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
import json
from typing import Optional, Dict, Any

logfire.configure()

def get_secret(secret_name: str = "LF_TOKEN", region_name: str = "eu-north-1") -> Optional[str]:
    
    with logfire.span(
        "get_secret", 
        secret_name=secret_name, 
        region=region_name
    ) as span:
        
        logfire.info(
            "Starting secret retrieval",
            secret_name=secret_name,
            region=region_name
        )
        
        try:
            session = boto3.session.Session()
            
            logfire.debug("Creating Secrets Manager client")
            client = session.client(
                service_name='secretsmanager',
                region_name=region_name
            )
            
            logfire.debug("Attempting to retrieve secret value")
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name
            )
            
            secret = get_secret_value_response['SecretString']
            
            span.set_attribute("secret_retrieved", True)
            span.set_attribute("secret_length", len(secret) if secret else 0)
            
            logfire.info(
                "Secret retrieved successfully",
                secret_name=secret_name,
                secret_length=len(secret) if secret else 0
            )
            
            return secret
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            span.set_attribute("error_type", "ClientError")
            span.set_attribute("error_code", error_code)
            span.record_exception(e)
            
            logfire.error(
                "AWS Secrets Manager client error",
                secret_name=secret_name,
                error_code=error_code,
                error_message=error_message,
                exc_info=e
            )
            
            if error_code == 'DecryptionFailureException':
                logfire.error("Secrets Manager can't decrypt the protected secret text using the provided KMS key")
            elif error_code == 'InternalServiceErrorException':
                logfire.error("An error occurred on the server side")
            elif error_code == 'InvalidParameterException':
                logfire.error("Invalid parameter provided")
            elif error_code == 'InvalidRequestException':
                logfire.error("Invalid request parameter")
            elif error_code == 'ResourceNotFoundException':
                logfire.error("The requested secret was not found")
            
            raise e
            
        except NoCredentialsError as e:
            span.set_attribute("error_type", "NoCredentialsError")
            span.record_exception(e)
            
            logfire.error(
                "AWS credentials not found",
                secret_name=secret_name,
                error_message="No AWS credentials configured",
                exc_info=e
            )
            raise e
            
        except BotoCoreError as e:
            span.set_attribute("error_type", "BotoCoreError")
            span.record_exception(e)
            
            logfire.error(
                "Boto3 core error occurred",
                secret_name=secret_name,
                error_message=str(e),
                exc_info=e
            )
            raise e
            
        except Exception as e:
            span.set_attribute("error_type", "UnexpectedError")
            span.record_exception(e)
            
            logfire.error(
                "Unexpected error during secret retrieval",
                secret_name=secret_name,
                error_message=str(e),
                exc_info=e
            )
            raise e


def get_secret_as_json(secret_name: str = "LF_TOKEN", region_name: str = "eu-north-1") -> Optional[Dict[Any, Any]]:
    
    with logfire.span(
        "get_secret_as_json",
        secret_name=secret_name,
        region=region_name
    ) as span:
        
        try:
            secret_string = get_secret(secret_name, region_name)
            
            if not secret_string:
                logfire.warning("No secret value retrieved")
                return None
            
            logfire.debug("Parsing secret as JSON")
            secret_dict = json.loads(secret_string)
            
            span.set_attribute("json_parsed", True)
            span.set_attribute("json_keys_count", len(secret_dict) if isinstance(secret_dict, dict) else 0)
            
            logfire.info(
                "Secret parsed as JSON successfully",
                secret_name=secret_name,
                keys_count=len(secret_dict) if isinstance(secret_dict, dict) else 0
            )
            
            return secret_dict
            
        except json.JSONDecodeError as e:
            span.set_attribute("error_type", "JSONDecodeError")
            span.record_exception(e)
            
            logfire.error(
                "Failed to parse secret as JSON",
                secret_name=secret_name,
                error_message=str(e),
                exc_info=e
            )
            raise e


def test_secret_retrieval():
    with logfire.span("test_secret_retrieval"):
        
        logfire.info("Starting secret retrieval test")
        
        try:
            secret = get_secret()
            
            if secret:
                logfire.info(
                    "Test successful - secret retrieved",
                    secret_length=len(secret)
                )
                print("Secret retrieved successfully!")
            else:
                logfire.warning("Test completed but no secret retrieved")
                print("No secret retrieved")
                
        except Exception as e:
            logfire.error(
                "Test failed with error",
                error_message=str(e),
                exc_info=e
            )
            print(f"Error retrieving secret: {e}")


if __name__ == "__main__":
    test_secret_retrieval() 