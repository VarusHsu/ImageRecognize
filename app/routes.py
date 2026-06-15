from flask import Blueprint, jsonify, render_template, request

from app.recognition import RecognitionError, recognize_s3_image
from app.s3 import create_upload_presigned_url

api = Blueprint("api", __name__)


@api.get("/")
def index():
    return render_template("index.html")


@api.get("/health")
def health_check():
    return jsonify({"status": "ok"})


@api.post("/recognize")
def recognize_image():
    payload = request.get_json(silent=True) or {}
    bucket = str(payload.get("bucket", "")).strip()
    key = str(payload.get("key", "")).strip()
    filename = payload.get("filename")
    content_type = payload.get("content_type")

    if not bucket:
        return jsonify({"error": "bucket is required"}), 400
    if not key:
        return jsonify({"error": "key is required"}), 400
    if content_type is not None:
        content_type = str(content_type).strip() or None

    try:
        record = recognize_s3_image(
            bucket=bucket,
            key=key,
            filename=str(filename).strip() if filename else None,
            content_type=content_type,
        )
    except RecognitionError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify(record)


@api.post("/uploads/presigned-url")
def create_presigned_upload_url():
    payload = request.get_json(silent=True) or {}
    filename = str(payload.get("filename", "")).strip()
    content_type = payload.get("content_type")

    if not filename:
        return jsonify({"error": "filename is required"}), 400
    if content_type is not None:
        content_type = str(content_type).strip()
    if content_type == "":
        content_type = None
    if content_type and not content_type.startswith("image/"):
        return jsonify({"error": "content_type must be an image MIME type"}), 400

    try:
        presigned_upload = create_upload_presigned_url(filename, content_type)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 500
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(presigned_upload)
