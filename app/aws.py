import boto3
from flask import current_app


def create_s3_client():
    config = current_app.config
    client_kwargs = {
        "region_name": config.get("AWS_REGION"),
    }

    if config.get("AWS_ACCESS_KEY_ID"):
        client_kwargs["aws_access_key_id"] = config["AWS_ACCESS_KEY_ID"]
    if config.get("AWS_SECRET_ACCESS_KEY"):
        client_kwargs["aws_secret_access_key"] = config["AWS_SECRET_ACCESS_KEY"]
    if config.get("AWS_SESSION_TOKEN"):
        client_kwargs["aws_session_token"] = config["AWS_SESSION_TOKEN"]

    return boto3.client("s3", **client_kwargs)
