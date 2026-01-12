# database.py
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

# ----------------------------------------------------------
#  SQLite configuration  (stored locally on Render free tier)
# ----------------------------------------------------------
Base = declarative_base()
engine = create_engine("sqlite:///duoobot.db", echo=False)
SessionLocal = sessionmaker(bind=engine)

# ----------------------------------------------------------
#  Lead table — stores all enquiry details
# ----------------------------------------------------------
class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    name = Column(String(80))
    project = Column(String(100))          # e.g. "e‑commerce website"
    details = Column(Text)                 # additional notes or features list
    budget = Column(String(50))            # e.g. "₹ 10 – 30 k"
    contact = Column(String(100))          # email or phone
    has_logo = Column(Boolean, default=True)
    has_social = Column(Boolean, default=True)
    contains_payment = Column(Boolean, default=False)
    urgent = Column(Boolean, default=False)
    domain_name = Column(String(120))
    domain_available = Column(String(10))  # "yes"/"no"
    estimated_cost = Column(String(50))    # formatted e.g. "₹ 25 000"
    created_at = Column(DateTime, default=datetime.utcnow)

# ----------------------------------------------------------
#  Optional Chat log table (if you want to record messages)
# ----------------------------------------------------------
class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(100))          # Firebase UID or guest ID
    message = Column(Text)
    is_bot = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# ----------------------------------------------------------
#  Create all tables if not already present
# ----------------------------------------------------------
Base.metadata.create_all(engine)