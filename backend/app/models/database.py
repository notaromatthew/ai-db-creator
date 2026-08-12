from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON, ForeignKey, Float, Integer
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime, timezone
import uuid
from app.utils.logger import log


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=True)
    schema_json = Column(JSON, nullable=True)
    db_path = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)
    file_path = Column(String(512), nullable=False)
    content_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="documents")


class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scenario_name = Column(String(255), nullable=False)
    provider = Column(String(100), nullable=False)
    model_name = Column(String(100), nullable=False)
    norm3_score = Column(Float, nullable=False)
    relationship_f1 = Column(Float, nullable=False)
    cell_precision = Column(Float, nullable=False)
    latency_seconds = Column(Float, nullable=False)
    token_cost_estimate = Column(Float, nullable=False)
    details_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class UserVote(Base):
    __tablename__ = "user_votes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, nullable=True, index=True)
    benchmark_id = Column(String, nullable=True, index=True)
    user_id = Column(String(255), nullable=False)
    schema_rating = Column(Integer, nullable=False)  # 1 to 5
    data_rating = Column(Integer, nullable=False)    # 1 to 5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


_engine = None

def init_db(db_url: str | None = None):
    global _engine
    if _engine is not None and db_url is None:
        return _engine
    from app.config import settings
    target_url = db_url or settings.database_url
    _engine = create_engine(
        target_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,
    )
    Base.metadata.create_all(_engine)
    log.info(f"Database PostgreSQL online inizializzato: {target_url.split('@')[-1]}")
    return _engine


def get_session(engine=None):
    from sqlalchemy.orm import sessionmaker
    target_engine = engine or init_db()
    Session = sessionmaker(bind=target_engine)
    return Session()


def verify_schema_compatibility(engine) -> None:
    """Fail startup when an existing table is missing model columns; create_all cannot migrate it safely."""
    from sqlalchemy import inspect
    inspector = inspect(engine)
    mismatches = []
    for table in Base.metadata.sorted_tables:
        if inspector.has_table(table.name):
            actual = {column["name"] for column in inspector.get_columns(table.name)}
            missing = set(table.columns.keys()) - actual
            if missing:
                mismatches.append(f"{table.name}: missing {sorted(missing)}")
    if mismatches:
        raise RuntimeError("Database schema migration required; startup refused: " + "; ".join(mismatches))
