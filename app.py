from flask import Flask, request, jsonify
from flasgger import Swagger

app = Flask(__name__)

# Initialize Swagger UI
swagger = Swagger(app)

# Simple in‑memory session dictionary (resets when server restarts)
sessions = {}


# ---------- Helper Function ----------
def estimate_price(project_type: str) -> int:
    """Return an estimated starting price based on project type."""
    project_type = project_type.lower()
    if "website" in project_type:
        return 800
    if "app" in project_type:
        return 2000
    if "automation" in project_type or "bot" in project_type:
        return 1000
    return 1200


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
              example: "Hi there! I'm DuooBot 👋 What’s your name?"
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

    session_id = "default_user"
    context = sessions.get(session_id, {})

    reply = "Hello! I'm DuooBot — your smart tech enquiry assistant 🤖"

    # ---------- Rule‑Based Conversation Flow ----------
    if not context.get("name"):
        if text.lower() in ["hi", "hello", "hey"]:
            reply = "Hi there! I'm DuooBot 👋 What’s your name?"
        else:
            context["name"] = text.title()
            reply = (
                f"Nice to meet you, {context['name']}! "
                "What kind of project are you planning? (website, app, automation...)"
            )

    elif not context.get("project"):
        context["project"] = text
        reply = f"Great — a {text}! Could you describe what features or goals you’d like it to have?"

    elif not context.get("details"):
        context["details"] = text
        price = estimate_price(context["project"])
        reply = (
            f"Thanks! Based on what you described, the estimated starting price "
            f"is about **${price}**.\n\n"
            "Would you like our team to follow up by email or phone?"
        )

    else:
        reply = (
            "Fantastic! I've taken note of your enquiry 🎉 "
            "Our DuooBitss team will reach out soon. Anything else before we wrap up?"
        )

    sessions[session_id] = context
    return jsonify({"reply": reply, "context": context})


# ---------- Run the App ----------
if __name__ == "__main__":
    print("🚀 DuooBot server running... Swagger available at http://127.0.0.1:5000/apidocs")
    app.run(debug=True)