from flask import Flask, request, jsonify
from flasgger import Swagger
from flask_cors import CORS
import os
from conversation_flow import Conversation   # your existing conversation engine

app = Flask(__name__)
CORS(app)                                    # allow frontend access
swagger = Swagger(app)

# In‑memory conversation store (simple + free‑tier friendly)
# key = user.uid  or  "guest"
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
              example: "Hi there! I'm DuooBot 👋 What’s your name?"
            context:
              type: object
      400:
        description: Invalid input or missing text
    """
    # --- Parse and validate incoming data ---
    try:
        data = request.get_json(force=True)
    except Exception as err:
        return jsonify({"error": f"Invalid JSON data: {err}"}), 400

    text = (data.get("text") or "").strip()
    user_uid = (data.get("uid") or "guest").strip()

    if not text:
        return jsonify({"reply": "Please send some text to chat with me!"}), 400

    # Each UID gets its own independent Conversation instance
    convo = sessions.get(user_uid)
    if convo is None:
        convo = Conversation()
        sessions[user_uid] = convo

    # Generate reply and update session
    try:
        reply_text = convo.reply(text)
    except Exception as err:
        print(f"❌ Conversation error for {user_uid}: {err}")
        reply_text = "⚠️ Sorry, something went wrong on the server."

    sessions[user_uid] = convo  # update state

    return jsonify({"reply": reply_text, "context": convo.state})


# ---------- Run the App ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 DuooBot running on 0.0.0.0:{port} — Swagger UI: /apidocs")
    app.run(host="0.0.0.0", port=port, debug=False)