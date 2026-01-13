# ----------------------------------------------------------
#  DuooBot Database Model — Optimized for Render Free Tier
# ----------------------------------------------------------
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from contextlib import contextmanager
import os

# ----------------------------------------------------------
#  SQLite configuration — light, safe, self‑contained
# ----------------------------------------------------------
# • File resides beside the code; Render keeps it alive per container
# • echo=False → silence SQL logs for better performance
# • check_same_thread=False → shared access for Flask threads
# ----------------------------------------------------------
DB_NAME = "duoobot.db"
DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), DB_NAME)

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
)

Base = declarative_base()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# ----------------------------------------------------------
#  Lead table — customer enquiries & estimates
# ----------------------------------------------------------
class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=True)
    project = Column(String(100), nullable=True)          # e.g. "e‑commerce website"
    details = Column(Text, nullable=True)                 # list of selected features
    budget = Column(String(50), nullable=True)            # e.g. "₹ 10 – 30 k"
    contact = Column(String(100), nullable=True)          # optional email / phone
    has_logo = Column(Boolean, default=True)
    has_social = Column(Boolean, default=True)
    contains_payment = Column(Boolean, default=False)
    urgent = Column(Boolean, default=False)
    domain_name = Column(String(120), nullable=True)
    domain_available = Column(String(10), default="unknown")   # "yes" / "no" / "unknown"
    estimated_cost = Column(String(50), nullable=True)        # e.g. "₹ 25 000"
    created_at = Column(DateTime, default=datetime.utcnow)

# ----------------------------------------------------------
#  ChatLog — optional: stores every message exchange
# ----------------------------------------------------------
class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), index=True)             # Firebase UID or guest ID
    message = Column(Text)
    is_bot = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# ----------------------------------------------------------
#  ConversationState — optionally persist user memory
# ----------------------------------------------------------
class ConversationState(Base):
    __tablename__ = "conversation_states"

    id = Column(Integer, primary_key=True)
    user_uid = Column(String(120), unique=True, index=True)
    state_json = Column(Text)                             # serialized JSON of conversation
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ----------------------------------------------------------
#  Initialize database
# ----------------------------------------------------------
def init_db():
    """Creates all tables if not already present."""
    try:
        Base.metadata.create_all(engine)
        print(f"✅  Database initialized at {DB_PATH}")
    except Exception as err:
        print(f"❌  Database initialization error: {err}")

init_db()

# ----------------------------------------------------------
#  Utility context manager for safe session handling
# ----------------------------------------------------------
@contextmanager
def db_session_scope():
    """
    Provide a transactional scope for DB operations.

    Example usage:
    ----------------
    with db_session_scope() as session:
        lead = Lead(name="Aditya", project="Website")
        session.add(lead)
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as err:
        session.rollback()
        print(f"⚠️  DB error: {err}")
    finally:
        session.close()

# ----------------------------------------------------------
#  CLI helper — run directly to inspect DB path
# ----------------------------------------------------------
if __name__ == "__main__":
    print(f"📂 Database file located at: {DB_PATH}")
    print("Tables:", Base.metadata.tables.keys())