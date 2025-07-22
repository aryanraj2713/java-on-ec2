import os
import logfire
from logfire import configure
from typing import Optional

def setup_logfire(
    service_name: str = "java-app-deployment",
    environment: Optional[str] = None,
    debug: bool = False
):
    environment = environment or os.environ.get("ENVIRONMENT", "development")
    
    configure(
        service_name=service_name,
        service_version=os.environ.get("SERVICE_VERSION", "1.0.0"),
        environment=environment,
        token=os.environ.get("LOGFIRE_TOKEN"),
        console=logfire.ConsoleOptions(
            colors=True,
            verbose=debug,
            include_timestamps=True,
            min_log_level="DEBUG" if debug else "INFO"
        ),
        additional_config={
            "service.namespace": "java-deployment",
            "deployment.environment": environment,
            "aws.region": os.environ.get("AWS_REGION", "eu-north-1")
        }
    )
    
    logfire.info(
        "Logfire configured successfully",
        service_name=service_name,
        environment=environment,
        debug=debug
    )

def get_logfire_token_from_secrets() -> Optional[str]:
    try:
        from secrets_manager import get_secret
        
        logfire_token = get_secret(
            secret_name=os.environ.get("LOGFIRE_SECRET_NAME", "LF_TOKEN"),
            region_name=os.environ.get("AWS_REGION", "eu-north-1")
        )
        
        if logfire_token:
            os.environ["LOGFIRE_TOKEN"] = logfire_token
            return logfire_token
            
    except Exception as e:
        print(f"Failed to retrieve Logfire token from Secrets Manager: {e}")
    
    return os.environ.get("LOGFIRE_TOKEN")

def configure_for_production():
    token = get_logfire_token_from_secrets()
    
    if not token:
        raise ValueError("Logfire token not found in Secrets Manager or environment variables")
    
    setup_logfire(
        service_name="java-app-deployment-prod",
        environment="production",
        debug=False
    )

def configure_for_development():
    setup_logfire(
        service_name="java-app-deployment-dev",
        environment="development",
        debug=True
    )

def auto_configure():
    environment = os.environ.get("ENVIRONMENT", "development").lower()
    
    token = get_logfire_token_from_secrets()
    
    if environment in ["production", "prod"]:
        if token:
            setup_logfire(
                service_name="java-app-deployment-prod",
                environment="production",
                debug=False
            )
        else:
            raise ValueError("Logfire token not found in Secrets Manager or environment variables")
    elif environment in ["staging", "stage"]:
        if token:
            setup_logfire(
                service_name="java-app-deployment-staging",
                environment="staging",
                debug=False
            )
        else:
            configure_for_development()
    else:
        if token:
            setup_logfire(
                service_name="java-app-deployment-dev",
                environment="development",
                debug=True
            )
        else:
            print("Warning: Logfire token not found, using basic configuration")
            setup_logfire(
                service_name="java-app-deployment-dev",
                environment="development",
                debug=True
            )

if __name__ == "__main__":
    auto_configure()
    
    logfire.info("Testing Logfire configuration")
    
    with logfire.span("test_span"):
        logfire.debug("This is a debug message")
        logfire.info("This is an info message")
        logfire.warning("This is a warning message")
        
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            logfire.error("Caught test exception", exc_info=e) 