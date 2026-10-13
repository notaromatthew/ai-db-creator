from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON, ForeignKey, Float, Integer, Boolean, UniqueConstraint, Index, text
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime, timezone
import uuid
from app.utils.logger import log


class Base(DeclarativeBase):
    pass


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    """Utente dell'applicazione: l'identificativo e' il claim `sub` di Keycloak."""
    __tablename__ = "users"

    id = Column(String(255), primary_key=True)
    email = Column(String(320), nullable=True, index=True)
    display_name = Column(String(255), nullable=True)
    blocked = Column(Boolean, nullable=False, default=False)
    daily_ai_quota = Column(Integer, nullable=True)  # None = usa il valore predefinito
    created_at = Column(DateTime, default=_now)
    last_seen_at = Column(DateTime, default=_now)


class AppSetting(Base):
    """Impostazioni modificabili dall'admin senza redeploy (chiave/valore JSON)."""
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(JSON, nullable=True)
    updated_by = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id = Column(String(255), nullable=False)
    action = Column(String(100), nullable=False)
    target = Column(String(255), nullable=True)
    detail = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_now, index=True)


class UsageEvent(Base):
    """Una riga per ogni chiamata AI: serve alle quote e alla vista consumi dell'admin."""
    __tablename__ = "usage_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), nullable=False, index=True)
    project_id = Column(String, nullable=True)
    kind = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=_now, index=True)


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=True)
    schema_json = Column(JSON, nullable=True)
    db_path = Column(String(512), nullable=True)
    schema_finalized_at = Column(DateTime, nullable=True)  # schema reso definitivo: chat e modifiche si chiudono
    schema_version = Column(Integer, nullable=False, default=0)  # numero dell'ultima versione salvata dello schema
    target_dialect = Column(String(20), nullable=True)  # dialetto di destinazione scelto per l'esportazione
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    invites = relationship("ProjectInvite", cascade="all, delete-orphan")
    links = relationship("ProjectLink", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", cascade="all, delete-orphan")
    jobs = relationship("Job", cascade="all, delete-orphan")
    schema_versions = relationship("SchemaVersion", cascade="all, delete-orphan")
    query_history = relationship("QueryHistory", cascade="all, delete-orphan")


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "editor" | "viewer"
    invited_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=_now)

    project = relationship("Project", back_populates="members")


class ProjectInvite(Base):
    """Invito per chi non e' ancora registrato: diventa un membro al primo accesso con quell'email."""
    __tablename__ = "project_invites"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    email = Column(String(320), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    invited_by = Column(String(255), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_now)


class ProjectLink(Base):
    """Link pubblico in sola lettura (schema e dati). Si salva solo l'hash del token."""
    __tablename__ = "project_links"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True)
    created_by = Column(String(255), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_now)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)
    file_path = Column(String(512), nullable=False)
    content_summary = Column(Text, nullable=True)
    needs_ocr = Column(Boolean, nullable=False, default=False)  # PDF senza testo estraibile e senza OCR riuscito
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="documents")


class ChatMessage(Base):
    """Cronologia della chat di progettazione: sopravvive al riavvio e alla perdita di sessione."""
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_now, index=True)


JOB_KINDS = ("schema", "dati", "esportazione")
JOB_STATES = ("queued", "running", "done", "failed", "cancelled")


class Job(Base):
    """Lavoro lungo (schema, dati, esportazione): lo stato sopravvive alla chiusura della pagina."""
    __tablename__ = "jobs"
    # un solo lavoro schema/dati attivo per progetto, garantito dal database anche con richieste concorrenti
    __table_args__ = (
        Index("uq_jobs_active_project", "project_id", unique=True,
              sqlite_where=text("kind IN ('schema','dati') AND status IN ('queued','running')"),
              postgresql_where=text("kind IN ('schema','dati') AND status IN ('queued','running')")),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(String(255), nullable=False)
    kind = Column(String(20), nullable=False)  # schema | dati | esportazione
    status = Column(String(20), nullable=False, default="queued", index=True)  # queued | running | done | failed | cancelled
    progress = Column(Integer, nullable=False, default=0)  # 0-100
    error = Column(Text, nullable=True)
    params = Column(JSON, nullable=True)  # parametri della richiesta (mai segreti)
    result = Column(JSON, nullable=True)
    executor = Column(String(20), nullable=True)  # celery | thread
    created_at = Column(DateTime, default=_now, index=True)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


SCHEMA_ORIGINS = ("generazione", "chat", "manuale", "ripristino")


class SchemaVersion(Base):
    """Cronologia delle versioni dello schema: ogni modifica ne salva una."""
    __tablename__ = "schema_versions"
    __table_args__ = (UniqueConstraint("project_id", "version", name="uq_schema_version"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    schema_json = Column(JSON, nullable=False)
    author = Column(String(255), nullable=True)
    origin = Column(String(20), nullable=False)  # generazione | chat | manuale | ripristino
    created_at = Column(DateTime, default=_now)


class QueryHistory(Base):
    """Domande in linguaggio naturale e query eseguite, per progetto."""
    __tablename__ = "query_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(String(255), nullable=True)
    question = Column(Text, nullable=True)  # vuota se la query e' stata scritta a mano
    generated_sql = Column(Text, nullable=True)
    source = Column(String(20), nullable=False, default="query")  # query (generata) | execute (eseguita)
    outcome = Column(String(10), nullable=False)  # ok | errore
    rows = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=_now, index=True)


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


RUN_STATES = ("queued", "running", "done", "failed", "cancelled")


class ResearchRun(Base):
    """Un run di benchmark (dataset x condizione x modello x temperatura) dello strumento di ricerca."""
    __tablename__ = "research_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id = Column(String, nullable=True, index=True)
    dataset = Column(String(100), nullable=False, index=True)
    condition = Column(String(50), nullable=False, index=True)
    provider = Column(String(100), nullable=True)
    model = Column(String(100), nullable=False, index=True)
    temperature = Column(Float, nullable=True, index=True)
    run_index = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="queued", index=True)
    cancel_requested = Column(Boolean, nullable=False, default=False)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1 = Column(Float, nullable=True)
    value_accuracy = Column(Float, nullable=True)  # celle corrette sul totale delle celle confrontate
    judge_score = Column(Float, nullable=True)  # giudice LLM, 0-1
    tokens_in = Column(Integer, nullable=True)
    tokens_out = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    latency_s = Column(Float, nullable=True)
    per_table = Column(JSON, nullable=True)
    schema_json = Column(JSON, nullable=True)
    manifest = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=_now, index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)


class StudyParticipant(Base):
    """Partecipante allo studio: solo un id pseudonimo casuale e l'hash del codice di ritiro."""
    __tablename__ = "study_participants"
    # un solo partecipante attivo (non ritirato) per account, senza salvare l'id utente
    __table_args__ = (
        Index("uq_study_active_account", "account_hash", unique=True,
              sqlite_where=text("account_hash IS NOT NULL AND withdrawn_at IS NULL"),
              postgresql_where=text("account_hash IS NOT NULL AND withdrawn_at IS NULL")),
    )

    id = Column(String, primary_key=True)  # pseudonimo casuale, non collegato all'utente
    code_hash = Column(String(64), nullable=False, unique=True)
    # HMAC con sale del sub: impedisce iscrizioni multiple dello stesso account senza conservarne l'id
    account_hash = Column(String(64), nullable=True)
    arm = Column(String(20), nullable=False, index=True)  # manual | ai_only | ai_interface
    consent_version = Column(String(20), nullable=True)
    consented_at = Column(DateTime, nullable=True)
    demographics = Column(JSON, nullable=True)  # solo fasce e livelli, mai dati identificativi
    step = Column(String(20), nullable=False, default="consent")
    completed_at = Column(DateTime, nullable=True)
    withdrawn_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_now)


class StudyEvent(Base):
    __tablename__ = "study_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    participant_id = Column(String, ForeignKey("study_participants.id"), nullable=False, index=True)
    type = Column(String(40), nullable=False)
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_now, index=True)


class StudyResponse(Base):
    """Risposte del partecipante: nasa_tlx, sus, debrief e lo schema dell'editor manuale."""
    __tablename__ = "study_responses"
    __table_args__ = (UniqueConstraint("participant_id", "kind", name="uq_study_response"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    participant_id = Column(String, ForeignKey("study_participants.id"), nullable=False, index=True)
    kind = Column(String(20), nullable=False)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=_now)


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

def run_migrations(engine=None):
    """Porta lo schema alla versione corrente.

    - database nuovo (create_all ha gia' creato tutto): si marca come aggiornato;
    - database precedente senza versione Alembic: si parte dalla migrazione iniziale;
    - database gia' versionato: upgrade fino all'ultima.
    """
    from pathlib import Path
    from sqlalchemy import inspect

    script_dir = Path(__file__).resolve().parents[2] / "alembic"
    if not script_dir.exists():
        log.warning("Cartella alembic non trovata: migrazioni saltate")
        return
    from alembic import command
    from alembic.config import Config

    engine = engine or init_db()
    cfg = Config()
    cfg.set_main_option("script_location", str(script_dir))
    cfg.attributes["engine"] = engine
    tables = set(inspect(engine).get_table_names())
    columns = {c["name"] for c in inspect(engine).get_columns("projects")} if "projects" in tables else set()
    if "alembic_version" in tables:
        command.upgrade(cfg, "head")
    elif "projects" in tables and "owner_id" not in columns:
        # init_db ha appena creato (vuote) le tabelle nuove: vanno tolte perche' le crea la migrazione.
        from sqlalchemy import text
        with engine.begin() as conn:
            for name in ("study_responses", "study_events", "study_participants", "research_runs",
                         "jobs", "schema_versions", "query_history",
                         "chat_messages", "project_links", "project_invites", "project_members",
                         "usage_events", "admin_audit_log", "app_settings", "users"):
                if name in tables:
                    conn.execute(text(f"DROP TABLE {name}"))
        command.stamp(cfg, "c25c5721cbb9")
        command.upgrade(cfg, "head")
    else:
        command.stamp(cfg, "head")
