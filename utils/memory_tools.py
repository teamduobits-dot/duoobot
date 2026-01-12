import json
from database import Base, SessionLocal
from sqlalchemy import Column, Integer, String, Text

# Simple persistent serialized state
class ConversationState(Base):
    __tablename__ = "conversation_states"
    id = Column(Integer, primary_key=True)
    user_uid = Column(String(120), unique=True)
    state_json = Column(Text)
Base.metadata.create_all(bind=SessionLocal().bind)

def save_state(uid, state):
    session = SessionLocal()
    existing = session.query(ConversationState).filter_by(user_uid=uid).first()
    s = json.dumps(state)
    if existing:
        existing.state_json = s
    else:
        existing = ConversationState(user_uid=uid, state_json=s)
        session.add(existing)
    session.commit(); session.close()

def load_state(uid):
    session = SessionLocal()
    r = session.query(ConversationState).filter_by(user_uid=uid).first()
    session.close()
    return json.loads(r.state_json) if r else None