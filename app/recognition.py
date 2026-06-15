from functools import lru_cache
from io import BytesIO

from botocore.exceptions import BotoCoreError, ClientError
from flask import current_app

from app.aws import create_s3_client
from app.db import insert_recognition_record


class RecognitionError(RuntimeError):
    pass


def recognize_s3_image(
    *,
    bucket: str,
    key: str,
    filename: str | None,
    content_type: str | None,
) -> dict:
    try:
        image_bytes = download_s3_object(bucket, key)
        predictions = classify_image(image_bytes)
    except Exception as exc:
        error_message = str(exc)
        record = insert_recognition_record(
            {
                "filename": filename,
                "bucket": bucket,
                "object_key": key,
                "content_type": content_type,
                "model_name": current_app.config["IMAGENET_MODEL"],
                "predictions": [],
                "status": "failed",
                "error": error_message,
            }
        )
        raise RecognitionError(error_message) from exc

    top_prediction = predictions[0]
    return insert_recognition_record(
        {
            "filename": filename,
            "bucket": bucket,
            "object_key": key,
            "content_type": content_type,
            "model_name": current_app.config["IMAGENET_MODEL"],
            "top_label": top_prediction["label"],
            "top_confidence": top_prediction["confidence"],
            "predictions": predictions,
            "status": "success",
        }
    )


def download_s3_object(bucket: str, key: str) -> bytes:
    client = create_s3_client()
    try:
        response = client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()
    except (BotoCoreError, ClientError, KeyError) as exc:
        raise RecognitionError("failed to download image from S3") from exc


def classify_image(image_bytes: bytes) -> list[dict]:
    try:
        from PIL import Image, UnidentifiedImageError
    except ModuleNotFoundError as exc:
        raise RecognitionError("Pillow is not installed") from exc

    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise RecognitionError("uploaded object is not a valid image") from exc

    model, weights = load_imagenet_model()
    preprocess = weights.transforms()

    import torch

    batch = preprocess(image).unsqueeze(0)
    with torch.inference_mode():
        probabilities = model(batch).softmax(1)[0]

    top_probabilities, top_indexes = probabilities.topk(5)
    categories = weights.meta["categories"]
    return [
        {
            "label": categories[index],
            "confidence": round(float(probability), 6),
        }
        for probability, index in zip(top_probabilities, top_indexes)
    ]


@lru_cache(maxsize=1)
def load_imagenet_model():
    import torch
    from torchvision.models import ResNet50_Weights, resnet50

    weights = ResNet50_Weights.DEFAULT
    model = resnet50(weights=weights)
    model.eval()
    torch.set_num_threads(1)
    return model, weights
