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
import os

# ----------------------------------------------------------
#  SQLite configuration — small, safe, self‑contained
# ----------------------------------------------------------
# • file lives beside the code (Render keeps it while instance alive)
# • disable echo for silent performance
# • check_same_thread=False allows Flask threads to share engine safely
# ----------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "duoobot.db")
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False},
)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# ----------------------------------------------------------
#  Lead table — stores all enquiry details
# ----------------------------------------------------------
class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    name = Column(String(80))
    project = Column(String(100))           # e.g. "e‑commerce website"
    details = Column(Text)                  # list of selected features
    budget = Column(String(50))             # e.g. "₹ 10 – 30 k"
    contact = Column(String(100))           # optional email/phone
    has_logo = Column(Boolean, default=True)
    has_social = Column(Boolean, default=True)
    contains_payment = Column(Boolean, default=False)
    urgent = Column(Boolean, default=False)
    domain_name = Column(String(120))
    domain_available = Column(String(10))   # "yes" / "no"
    estimated_cost = Column(String(50))     # formatted e.g. "₹ 25 000"
    created_at = Column(DateTime, default=datetime.utcnow)


# ----------------------------------------------------------
#  ChatLog — optional: store every exchange
# ----------------------------------------------------------
class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(100))          # Firebase UID or guest ID
    message = Column(Text)
    is_bot = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


# ----------------------------------------------------------
#  ConversationState — persistent user memory (optional)
# ----------------------------------------------------------
class ConversationState(Base):
    __tablename__ = "conversation_states"

    id = Column(Integer, primary_key=True)
    user_uid = Column(String(120), unique=True)
    state_json = Column(Text)               # serialized self.state
    updated_at = Column(DateTime, default=datetime.utcnow)


# ----------------------------------------------------------
#  Database initialization
# ----------------------------------------------------------
Base.metadata.create_all(engine)

# ----------------------------------------------------------
#  Utility: context manager wrapper for safe sessions
# ----------------------------------------------------------
from contextlib import contextmanager

@contextmanager
def db_session_scope():
    """Provide transactional scope for DB operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as err:
        session.rollback()
        print(f"⚠️  DB error: {err}")
    finally:
        session.close()