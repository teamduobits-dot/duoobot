# -----------------------------------------------------------
#  DuooBot Backend — Flasgger Inline‑Model Edition (Ultimate Fix)
# -----------------------------------------------------------
from flask import Flask, request, jsonify
from flasgger import Swagger
from marshmallow import Schema, fields
from flask_cors import CORS
import os, uuid, json, socket

from conversation_flow import Conversation
from database import SessionLocal
from sqlalchemy import text as sql_text

# -----------------------------------------------------------
#  Flask + Swagger setup
# -----------------------------------------------------------
app = Flask(__name__)
CORS(app)

# --- Inline schema models (metadata keeps examples valid for Marshmallow) ---
class ChatBody(Schema):
    text = fields.Str(required=True, metadata={"example": "Build me a website"})
    uid = fields.Str(required=False, metadata={"example": "demo123"})
    displayName = fields.Str(required=False, metadata={"example": "Sandy"})

class ResetBody(Schema):
    uid = fields.Str(required=True, metadata={"example": "demo123"})

class DomainBody(Schema):
    domain = fields.Str(required=True, metadata={"example": "duobits"})
    tlds = fields.List(fields.Str(), metadata={"example": [".com", ".in", ".net"]})

# --- Force Flasgger to use explicit OpenAPI template (renders requestBody editor) ---
swagger_template = {
    "openapi": "3.0.0",
    "info": {
        "title": "DuooBot API Docs",
        "version": "1.0.0",
        "description": "Interactive Swagger UI for DuooBot endpoints"
    },
    "components": {
        "schemas": {
            "ChatBody": ChatBody().fields,
            "ResetBody": ResetBody().fields,
            "DomainBody": DomainBody().fields
        }
    }
}
app.config["SWAGGER"] = {"uiversion": 3, "openapi": "3.0.0"}
swagger = Swagger(app, template=swagger_template)

# -----------------------------------------------------------
#  In‑memory store + lightweight SQLite persistence
# -----------------------------------------------------------
sessions = {}
STATE_FILE = "convo_cache.json"

def save_state_to_file():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({uid: c.state for uid, c in sessions.items()}, f)
    except Exception as err:
        print("⚠️ Could not persist sessions:", err)

def load_state_from_file():
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for uid, st in data.items():
            sessions[uid] = Conversation(state=st)
        print(f"♻️ Restored {len(sessions)} conversation states from cache.")
    except Exception as err:
        print("⚠️ Failed to load cached state:", err)

load_state_from_file()

def prune_sessions(limit=100):
    if len(sessions) > limit:
        for uid in list(sessions.keys())[: len(sessions) - limit]:
            del sessions[uid]
        print(f"🧹 Pruned sessions to {limit} active users.")

# -----------------------------------------------------------
#  /chat
# -----------------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    """
    Chat with DuooBot
    ---
    post:
      summary: Send a user message and receive DuooBot's structured reply
      requestBody:
        required: true
        content:
          application/json:
            schema: ChatBody
      responses:
        200:
          description: Successful bot reply (JSON)
    """
    try:
        data = request.get_json(force=True)
    except Exception as err:
        return jsonify({"error": f"Invalid JSON: {err}"}), 400

    text = (data.get("text") or "").strip()
    uid = (data.get("uid") or "").strip() or f"guest_{uuid.uuid4().hex[:8]}"
    name = (data.get("displayName") or "").strip() or "Guest"

    if not text:
        return jsonify({"reply": {"text": "Please send some text!"}}), 400

    convo = sessions.get(uid) or Conversation(user_name=name)
    sessions[uid] = convo
    prune_sessions()

    try:
        reply_payload = convo.reply(text)
        if isinstance(reply_payload, str):
            reply_payload = {"text": reply_payload}
    except Exception as err:
        print(f"❌ Error for {uid}: {err}")
        reply_payload = {"text": "⚠️ Server error."}

    save_state_to_file()
    return jsonify({"reply": reply_payload, "context": convo.state, "user": uid})

# -----------------------------------------------------------
#  /reset
# -----------------------------------------------------------
@app.route("/reset", methods=["POST"])
def reset_conversation():
    """
    Reset a user's session
    ---
    post:
      summary: Clear a user’s saved conversation
      requestBody:
        required: true
        content:
          application/json:
            schema: ResetBody
      responses:
        200:
          description: Reset confirmation
    """
    try:
        data = request.get_json(force=True)
        uid = (data.get("uid") or "").strip()
        if not uid:
            return jsonify({"error": "Missing uid"}), 400
        sessions.pop(uid, None)
        save_state_to_file()
        print(f"🗑️ Conversation reset for user {uid}")
        return jsonify({"status": "reset", "message": "Conversation cleared successfully"})
    except Exception as err:
        print(f"❌ Reset error: {err}")
        return jsonify({"error": str(err)}), 500

# -----------------------------------------------------------
#  /domaincheck
# -----------------------------------------------------------
@app.route("/domaincheck", methods=["POST"])
def domain_check():
    """
    Domain Availability Check
    ---
    post:
      summary: Check whether given domain TLDs are available
      requestBody:
        required: true
        content:
          application/json:
            schema: DomainBody
      responses:
        200:
          description: Availability results array
    """
    try:
        data = request.get_json(force=True)
        base = (data.get("domain") or "").strip().lower()
        tlds = data.get("tlds") or [".com", ".in", ".net", ".org", ".co"]
        if not base:
            return jsonify({"error": "Missing domain parameter"}), 400

        socket.setdefaulttimeout(2)
        results = []
        for tld in tlds:
            name = f"{base}{tld}"
            try:
                socket.gethostbyname(name)
                available = False
            except socket.gaierror:
                available = True
            results.append({"tld": tld, "domain": name, "available": available})
        return jsonify({"base": base, "domains": results})
    except Exception as err:
        print("❌ Domain check error:", err)
        return jsonify({"error": str(err)}), 500

# -----------------------------------------------------------
#  /health
# -----------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    """DB connectivity check"""
    try:
        s = SessionLocal()
        s.execute(text("SELECT 1"))
        s.close()
    except Exception as err:
        print("⚠️ Healthcheck DB ping failed:", err)
    return jsonify({"status": "ok"}), 200

# -----------------------------------------------------------
#  Run locally or on Render
# -----------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 DuooBot running at http://127.0.0.1:{port}/apidocs — Swagger UI ready.")
    app.run(host="0.0.0.0", port=port, debug=False)