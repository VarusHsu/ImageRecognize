# Image Recognition Service

Flask scaffold for an image recognition service.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Configuration

Copy `config.example.toml` to `config.toml` and fill in the values for your environment:

```bash
cp config.example.toml config.toml
```

Application settings are loaded from `config.toml`, including AWS access key
settings used by the S3 client. Keep the local `config.toml` out of version
control because it contains credentials.

Recognition records are stored in MySQL. The service creates the configured
database and `recognition_records` table automatically when the first record is
written, assuming the MySQL user has permission.

## Endpoints

- `GET /health`: service health check.
- `POST /uploads/presigned-url`: create an S3 presigned URL for direct image upload. If `content_type` is provided, it must be an `image/*` MIME type.
- `POST /recognize`: recognize an uploaded S3 image with an ImageNet pretrained model and save the recognition record to MySQL.

### Create Upload URL

Request:

```bash
curl -X POST http://localhost:5001/uploads/presigned-url \
  -H "Content-Type: application/json" \
  -d '{"filename":"cat.jpg","content_type":"image/jpeg"}'
```

Response:

```json
{
  "upload_url": "https://...",
  "bucket": "your-bucket-name",
  "key": "uploads/...",
  "method": "PUT",
  "expires_in": 900,
  "headers": {
    "Content-Type": "image/jpeg"
  }
}
```

### Recognize Uploaded Image

Request:

```bash
curl -X POST http://localhost:5001/recognize \
  -H "Content-Type: application/json" \
  -d '{"bucket":"your-bucket-name","key":"uploads/cat.jpg","filename":"cat.jpg","content_type":"image/jpeg"}'
```

Response:

```json
{
  "id": 1,
  "filename": "cat.jpg",
  "bucket": "your-bucket-name",
  "key": "uploads/cat.jpg",
  "model_name": "resnet50",
  "top_label": "tabby",
  "top_confidence": 0.832141,
  "predictions": [
    {
      "label": "tabby",
      "confidence": 0.832141
    }
  ],
  "status": "success",
  "created_at": "2026-06-15T15:00:00.000000"
}
```
