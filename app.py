# -----------------------------------------------------------
#  DuooBot Backend — Smarter Local Edition (Render Free Tier)
# -----------------------------------------------------------
from flask import Flask, request, jsonify
from flasgger import Swagger
from flask_cors import CORS
import os
import uuid
import json
from conversation_flow import Conversation
from database import SessionLocal
from sqlalchemy import text as sql_text

# -----------------------------------------------------------
#  Flask + Swagger setup
# -----------------------------------------------------------
app = Flask(__name__)
CORS(app)
swagger = Swagger(app)

# -----------------------------------------------------------
#  In‑memory store  +  lightweight SQLite persistence
# -----------------------------------------------------------
sessions = {}

STATE_FILE = "convo_cache.json"  # quick backup between restarts


def save_state_to_file():
    """Write minimal session state to disk (for Render restarts)."""
    try:
        snap = {uid: c.state for uid, c in sessions.items()}
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(snap, f)
    except Exception as err:
        print(f"⚠️  Could not persist sessions: {err}")


def load_state_from_file():
    """Load any previous cached state snapshot."""
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for uid, st in data.items():
                sessions[uid] = Conversation(state=st)
        print(f"♻️  Restored {len(sessions)} conversation states from cache.")
    except Exception as err:
        print(f"⚠️  Failed to load cached state: {err}")


load_state_from_file()

# -----------------------------------------------------------
#  Helper: prune inactive sessions (Render free memory)
# -----------------------------------------------------------
def prune_sessions(limit=100):
    if len(sessions) > limit:
        # discard oldest by history length heuristic
        sorted_uids = sorted(
            sessions.keys(),
            key=lambda u: len(sessions[u].state.get("history", [])),
        )
        for uid in sorted_uids[: len(sessions) - limit]:
            del sessions[uid]
        print(f"🧹  Pruned sessions to {limit} active users.")


# -----------------------------------------------------------
#  Chat Endpoint
# -----------------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    """
    Chat with DuooBot
    ---
    description: Send a message to DuooBot and receive a structured reply
    """
    try:
        data = request.get_json(force=True)
    except Exception as err:
        return jsonify({"error": f"Invalid JSON: {err}"}), 400

    text = (data.get("text") or "").strip()
    user_uid = (data.get("uid") or "").strip()
    display_name = (data.get("displayName") or "").strip()

    if not text:
        return jsonify({"reply": {"text": "Please send some text!"}}), 400

    # Assign guest ID if none
    if not user_uid:
        user_uid = f"guest_{uuid.uuid4().hex[:8]}"

    # Retrieve or create a conversation
    convo = sessions.get(user_uid)
    if convo is None:
        convo = Conversation(user_name=display_name or "Guest")
        sessions[user_uid] = convo
        prune_sessions()

    # Generate reply
    try:
        reply_payload = convo.reply(text)
        if isinstance(reply_payload, str):
            reply_payload = {"text": reply_payload}
    except Exception as err:
        print(f"❌  Error during conversation for {user_uid}: {err}")
        reply_payload = {
            "text": "⚠️ Sorry, something went wrong on the server. Please try again."
        }

    # Save state
    sessions[user_uid] = convo
    save_state_to_file()

    return jsonify(
        {"reply": reply_payload, "context": convo.state, "user": user_uid}
    )


# -----------------------------------------------------------
#  Reset conversation endpoint (frontend “delete chat” button)
# -----------------------------------------------------------
@app.route("/reset", methods=["POST"])
def reset_conversation():
    """
    Clears an in‑memory + cached conversation for a given UID
    """
    try:
        data = request.get_json(force=True)
        user_uid = (data.get("uid") or "").strip()
        if not user_uid:
            return jsonify({"error": "Missing uid"}), 400

        if user_uid in sessions:
            del sessions[user_uid]
            save_state_to_file()
            print(f"🗑️  Conversation reset for user {user_uid}")

        return jsonify(
            {"status": "reset", "message": "Conversation cleared successfully"}
        )
    except Exception as err:
        print(f"❌  Error during conversation reset: {err}")
        return jsonify({"error": str(err)}), 500


# -----------------------------------------------------------
#  Domain Availability API  (optional standalone use)
# -----------------------------------------------------------
@app.route("/domaincheck", methods=["GET"])
def domain_check():
    name = (request.args.get("domain") or "").strip().lower()
    if not name:
        return jsonify({"error": "Missing ?domain=example.com"}), 400
    try:
        convo = Conversation()
        available = convo.check_domain(name)
        return jsonify({"domain": name, "available": available})
    except Exception as err:
        return jsonify({"error": str(err)}), 500


# -----------------------------------------------------------
#  Health‑check endpoint (Render uptime pinger)
# -----------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    try:
        # simple DB ping keeps SQLite file unlocked
        s = SessionLocal()
        s.execute(sql_text("SELECT 1"))
        s.close()
    except Exception as err:
        print(f"⚠️  Healthcheck DB ping failed: {err}")
    return jsonify({"status": "ok"}), 200


# -----------------------------------------------------------
#  Run locally or on Render
# -----------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(
        f"🚀  DuooBot running on 0.0.0.0:{port} — Swagger UI → /apidocs\n"
        "💾  Memory‑safe mode active (Render Free Tier)"
    )
    app.run(host="0.0.0.0", port=port, debug=False)