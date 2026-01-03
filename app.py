from flask import Flask, request, jsonify
from flasgger import Swagger
from flask_cors import CORS
import os
from conversation_flow import Conversation   # import your existing conversation logic

# -----------------------------------------------------------
#  Flask application setup
# -----------------------------------------------------------
app = Flask(__name__)
CORS(app)                      # allow frontend access
swagger = Swagger(app)

# -----------------------------------------------------------
#  In‑memory conversation store
#  (key = Firebase UID or temporary guest key)
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
    user_uid = (data.get("uid") or "").strip()

    if not text:
        return jsonify({"reply": "Please send some text to chat with me!"}), 400

    # If user not logged in, create a lightweight guest session ID
    if not user_uid:
        ip = request.remote_addr or "anon"
        user_uid = f"guest_{ip}"

    # Retrieve or create a unique conversation for this session ID
    convo = sessions.get(user_uid)
    if convo is None:
        convo = Conversation()
        sessions[user_uid] = convo

    # Generate bot reply
    try:
        reply_text = convo.reply(text)
    except Exception as err:
        print(f"❌ Error in conversation for {user_uid}: {err}")
        reply_text = "⚠️ Sorry, something went wrong on the server."

    # Save updated conversation state
    sessions[user_uid] = convo

    return jsonify({
        "reply": reply_text,
        "context": convo.state,
    })


# -----------------------------------------------------------
#  Run the App (local/dev entry)
# -----------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 DuooBot running on 0.0.0.0:{port} — Swagger UI: /apidocs")
    app.run(host="0.0.0.0", port=port, debug=False)