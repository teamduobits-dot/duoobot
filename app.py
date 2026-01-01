from flask import Flask, request, jsonify
from flasgger import Swagger
from flask_cors import CORS
import os
from conversation_flow import Conversation   # 👈 new modular engine

app = Flask(__name__)
CORS(app)                   # enable CORS for all routes
swagger = Swagger(app)

# in‑memory session store (you can replace with DB later)
sessions = {}

# ---------- Chat Endpoint ----------
@app.route("/chat", methods=["POST"])
def chat():
    """
    Chat with DuooBot
    ---
    description: Send a message to DuooBot and receive a friendly reply.
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
              example: "Hello"
    responses:
      200:
        description: Successful bot reply
        schema:
          type: object
          properties:
            reply:
              type: string
              example: "Hi there! I'm DuooBot 👋 What’s your name?"
            context:
              type: object
      400:
        description: Invalid input or missing text
    """
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON data"}), 400

    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"reply": "Please send some text to chat with me!"}), 400

    # one shared demo session (replace with user id or cookie later)
    session_id = "default_user"

    # get previous conversation or start new
    convo = sessions.get(session_id)
    if not convo:
        convo = Conversation()

    # generate reply + update state
    reply = convo.reply(text)
    sessions[session_id] = convo

    return jsonify({"reply": reply, "context": convo.state})


# ---------- Run the App ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 DuooBot running on 0.0.0.0:{port} — Swagger at /apidocs")
    app.run(host="0.0.0.0", port=port, debug=False)