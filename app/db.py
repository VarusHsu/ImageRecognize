from datetime import UTC, datetime

from flask import current_app, g
from sqlalchemy import JSON, BigInteger, Float, Index, String, Text, create_engine, text
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class RecognitionRecord(Base):
    __tablename__ = "recognition_records"
    __table_args__ = (
        Index("idx_created_at", "created_at"),
        Index("idx_object_key", "object_key", mysql_length=255),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    filename: Mapped[str | None] = mapped_column(String(512))
    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255))
    model_name: Mapped[str | None] = mapped_column(String(128))
    top_label: Mapped[str | None] = mapped_column(String(255))
    top_confidence: Mapped[float | None] = mapped_column(Float)
    predictions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)


SessionLocal = sessionmaker(expire_on_commit=False)


def init_db(app) -> None:
    app.config["MYSQL_PORT"] = int(app.config["MYSQL_PORT"])
    app.teardown_appcontext(close_db_session)


def insert_recognition_record(record: dict) -> dict:
    ensure_schema()
    created_at = datetime.now(UTC).replace(tzinfo=None)
    predictions = record.get("predictions") or []
    db_record = RecognitionRecord(
        filename=record.get("filename"),
        bucket=record["bucket"],
        object_key=record["object_key"],
        content_type=record.get("content_type"),
        model_name=record.get("model_name"),
        top_label=record.get("top_label"),
        top_confidence=record.get("top_confidence"),
        predictions=predictions,
        status=record["status"],
        error=record.get("error"),
        created_at=created_at,
    )

    session = get_db_session()
    session.add(db_record)
    session.commit()

    return serialize_record(db_record)


def get_db_session() -> Session:
    if "db_session" not in g:
        g.db_session = SessionLocal(bind=get_engine())
    return g.db_session


def close_db_session(error: Exception | None = None) -> None:
    session = g.pop("db_session", None)
    if session is None:
        return
    if error is not None:
        session.rollback()
    session.close()


def ensure_schema() -> None:
    if current_app.config.get("_DB_SCHEMA_READY"):
        return

    database = current_app.config["MYSQL_DATABASE"]
    charset = current_app.config["MYSQL_CHARSET"]
    if charset not in {"utf8", "utf8mb4"}:
        raise RuntimeError("MYSQL_CHARSET must be utf8 or utf8mb4")

    server_engine = create_engine(
        build_database_url(include_database=False), future=True
    )
    with server_engine.begin() as connection:
        connection.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS {quote_identifier(database)} "
                f"DEFAULT CHARACTER SET {charset} COLLATE {charset}_unicode_ci"
            )
        )
    server_engine.dispose()

    Base.metadata.create_all(get_engine())
    current_app.config["_DB_SCHEMA_READY"] = True


def get_engine():
    engine = current_app.config.get("_DB_ENGINE")
    if engine is None:
        engine = create_engine(
            build_database_url(include_database=True),
            pool_pre_ping=True,
            future=True,
        )
        current_app.config["_DB_ENGINE"] = engine
    return engine


def build_database_url(include_database: bool = True) -> URL:
    config = current_app.config
    return URL.create(
        "mysql+pymysql",
        username=config["MYSQL_USER"],
        password=config["MYSQL_PASSWORD"],
        host=config["MYSQL_HOST"],
        port=int(config["MYSQL_PORT"]),
        database=config["MYSQL_DATABASE"] if include_database else None,
        query={"charset": config["MYSQL_CHARSET"]},
    )


def quote_identifier(value: str) -> str:
    return f"`{value.replace('`', '``')}`"


def serialize_record(record: RecognitionRecord) -> dict:
    return {
        "id": record.id,
        "filename": record.filename,
        "bucket": record.bucket,
        "key": record.object_key,
        "content_type": record.content_type,
        "model_name": record.model_name,
        "top_label": record.top_label,
        "top_confidence": record.top_confidence,
        "predictions": record.predictions,
        "status": record.status,
        "error": record.error,
        "created_at": record.created_at.isoformat(),
    }
