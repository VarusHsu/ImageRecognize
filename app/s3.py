import os
from pathlib import PurePath
from uuid import uuid4

from botocore.exceptions import BotoCoreError, ClientError
from flask import current_app

from app.aws import create_s3_client


def create_upload_presigned_url(filename: str, content_type: str | None) -> dict:
    bucket = current_app.config.get("S3_BUCKET")
    if not bucket:
        raise ValueError("S3 bucket is not configured")

    key = build_object_key(filename)
    params = {
        "Bucket": bucket,
        "Key": key,
    }
    if content_type:
        params["ContentType"] = content_type

    client = create_s3_client()
    try:
        upload_url = client.generate_presigned_url(
            ClientMethod="put_object",
            Params=params,
            ExpiresIn=int(current_app.config["S3_PRESIGNED_EXPIRES_SECONDS"]),
            HttpMethod="PUT",
        )
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError("failed to generate S3 presigned URL") from exc

    return {
        "upload_url": upload_url,
        "bucket": bucket,
        "key": key,
        "method": "PUT",
        "expires_in": int(current_app.config["S3_PRESIGNED_EXPIRES_SECONDS"]),
        "headers": {"Content-Type": content_type} if content_type else {},
    }


def build_object_key(filename: str) -> str:
    safe_name = PurePath(filename).name.strip()
    if not safe_name:
        safe_name = "image"

    prefix = str(current_app.config.get("S3_UPLOAD_PREFIX", "uploads")).strip("/")
    unique_name = f"{uuid4().hex}-{safe_name}"
    return os.path.join(prefix, unique_name) if prefix else unique_name
