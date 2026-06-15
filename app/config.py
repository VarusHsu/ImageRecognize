from pathlib import Path
import tomllib


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config.toml"
EXAMPLE_CONFIG_PATH = BASE_DIR / "config.example.toml"


def load_config(config_path: str | Path | None = None) -> dict:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        path = EXAMPLE_CONFIG_PATH

    with path.open("rb") as file:
        raw_config = tomllib.load(file)

    return flatten_config(raw_config)


def flatten_config(raw_config: dict) -> dict:
    aws = raw_config.get("aws", {})
    database = raw_config.get("database", {})
    flask = raw_config.get("flask", {})
    imagenet = raw_config.get("imagenet", {})
    s3 = raw_config.get("s3", {})
    server = raw_config.get("server", {})

    return {
        "AWS_ACCESS_KEY_ID": aws.get("access_key_id"),
        "AWS_REGION": aws.get("region"),
        "AWS_SECRET_ACCESS_KEY": aws.get("secret_access_key"),
        "AWS_SESSION_TOKEN": aws.get("session_token"),
        "IMAGENET_MODEL": imagenet.get("model", "resnet50"),
        "JSON_AS_ASCII": flask.get("json_as_ascii", False),
        "MAX_CONTENT_LENGTH": int(flask.get("max_content_length", 16 * 1024 * 1024)),
        "MYSQL_CHARSET": database.get("charset", "utf8mb4"),
        "MYSQL_DATABASE": database.get("database", "image_recognition"),
        "MYSQL_HOST": database.get("host", "127.0.0.1"),
        "MYSQL_PASSWORD": database.get("password", ""),
        "MYSQL_PORT": int(database.get("port", 3306)),
        "MYSQL_USER": database.get("user", "root"),
        "S3_BUCKET": s3.get("bucket"),
        "S3_PRESIGNED_EXPIRES_SECONDS": int(s3.get("presigned_expires_seconds", 900)),
        "S3_UPLOAD_PREFIX": s3.get("upload_prefix", "uploads"),
        "SERVER_DEBUG": bool(server.get("debug", True)),
        "SERVER_HOST": server.get("host", "0.0.0.0"),
        "SERVER_PORT": int(server.get("port", 5000)),
    }
