# app.py
from flask import Flask, request, jsonify
from flasgger import Swagger
from flask_cors import CORS
import os
import uuid
from conversation_flow import Conversation   # updated Conversation class

# -----------------------------------------------------------
#  Flask application setup
# -----------------------------------------------------------
app = Flask(__name__)
CORS(app)
swagger = Swagger(app)

# -----------------------------------------------------------
#  In‑memory conversation store  (uid → Conversation instance)
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
    description: Send a message to DuooBot and receive a structured reply
                 (text + optional button options).
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
              example: "E‑commerce website"
            uid:
              type: string
              example: "firebase_uid_abc123"
            displayName:
              type: string
              example: "Vishal Sharma"
    responses:
      200:
        description: Bot reply payload
        schema:
          type: object
          properties:
            reply:
              type: object
            context:
              type: object
      400:
        description: Invalid input
    """
    # --- Parse and validate JSON -----------------------------
    try:
        data = request.get_json(force=True)
    except Exception as err:
        return jsonify({"error": f"Invalid JSON: {err}"}), 400

    text = (data.get("text") or "").strip()
    user_uid = (data.get("uid") or "").strip()
    display_name = (data.get("displayName") or "").strip()

    if not text:
        return jsonify({"reply": {"text": "Please send some text!"}}), 400

    # --- Assign guest ID if needed ----------------------------
    if not user_uid:
        user_uid = f"guest_{uuid.uuid4().hex[:8]}"

    # --- Retrieve or create conversation ----------------------
    convo = sessions.get(user_uid)
    if convo is None:
        # Pass the display name (fetched from Google auth)
        convo = Conversation(user_name=display_name)
        sessions[user_uid] = convo

    # --- Generate bot reply -----------------------------------
    try:
        reply_payload = convo.reply(text)
        # reply_payload can be string or dict; normalize
        if isinstance(reply_payload, str):
            reply_payload = {"text": reply_payload}
    except Exception as err:
        print(f"❌  Error during conversation for {user_uid}: {err}")
        reply_payload = {
            "text": "⚠️ Sorry, something went wrong on the server."
        }

    # --- Save conversation state ------------------------------
    sessions[user_uid] = convo

    # --- Return structured response ----------------------------
    return jsonify({
        "reply": reply_payload,
        "context": convo.state,
        "user": user_uid
    })


# -----------------------------------------------------------
#  Domain Availability API (optional standalone use)
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
#  Health‑check endpoint (keeps Render happy)
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