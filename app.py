# app.py
from flask import Flask, request, jsonify
from flasgger import Swagger
from flask_cors import CORS
import os
import uuid
from conversation_flow import Conversation   # your upgraded class

# -----------------------------------------------------------
#  Flask application setup
# -----------------------------------------------------------
app = Flask(__name__)
CORS(app)
swagger = Swagger(app)

# -----------------------------------------------------------
#  In‑memory conversation store  (uid -> Conversation object)
# -----------------------------------------------------------
sessions = {}

# -----------------------------------------------------------
#  Chat Endpoint
# -----------------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    """
    Chat with DuooBot
    ---
    description: Send a message to DuooBot and receive a friendly reply in INR estimates.
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            text:
              type: string
              example: "Hello there!"
            uid:
              type: string
              example: "user_123abc"
    responses:
      200:
        description: Successful bot reply
        schema:
          type: object
          properties:
            reply:
              type: string
            context:
              type: object
      400:
        description: Invalid input or missing text
    """
    # --- Parse JSON safely -----------------------------------
    try:
        data = request.get_json(force=True)
    except Exception as err:
        return jsonify({"error": f"Invalid JSON: {err}"}), 400

    text = (data.get("text") or "").strip()
    user_uid = (data.get("uid") or "").strip()

    if not text:
        return jsonify({"reply": "Please send some text to chat with me!"}), 400

    # --- Assign a safe guest ID if user not logged in --------
    if not user_uid:
        user_uid = f"guest_{uuid.uuid4().hex[:8]}"

    # --- Retrieve or start new conversation ------------------
    convo = sessions.get(user_uid)
    if convo is None:
        convo = Conversation()
        sessions[user_uid] = convo

    # --- Generate bot reply ----------------------------------
    try:
        reply_text = convo.reply(text)
    except Exception as err:
        print(f"❌  Error for {user_uid}: {err}")
        reply_text = "⚠️  Sorry, something went wrong on the server."

    # --- Save updated state (conversation persists in memory) ---
    sessions[user_uid] = convo

    return jsonify({
        "reply": reply_text,
        "context": convo.state,
        "user": user_uid
    })

# -----------------------------------------------------------
#  Optional: simple Domain Availability API
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
#  Health‑check endpoint (for Render monitoring)
# -----------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

# -----------------------------------------------------------
#  Run locally or on Render
# -----------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀  DuooBot running on 0.0.0.0:{port}  —  Swagger UI → /apidocs")
    app.run(host="0.0.0.0", port=port, debug=False)