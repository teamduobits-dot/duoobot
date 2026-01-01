class Conversation:
    def __init__(self, state=None):
        # store everything about the chat in self.state
        self.state = state or {"step": "greet"}

    def reply(self, text: str):
        step = self.state["step"]
        text = text.lower().strip()

        # ---------- Greeting ----------
        if step == "greet":
            self.state["step"] = "get_name"
            return "👋 Hi! I'm DuooBot — your tech assistant at DuooBits. What's your name?"

        # ---------- Get Name ----------
        elif step == "get_name":
            self.state["name"] = text.title()
            self.state["step"] = "project_type"
            return (
                f"Nice to meet you, {self.state['name']}! "
                "What kind of project are you planning — website, app, or automation?"
            )

        # ---------- Project Type ----------
        elif step == "project_type":
            self.state["project"] = text
            self.state["step"] = "details"
            return (
                f"Great — a {self.state['project']}! "
                "Could you describe the main features you need?"
            )

        # ---------- Project Details ----------
        elif step == "details":
            self.state["details"] = text
            self.state["step"] = "quote"
            cost = self.estimate_price(text)
            return (
                f"Understood. Your starting estimate is around ${cost}. "
                "Would you like to share your contact email so we can follow up?"
            )

        # ---------- Contact / Quote ----------
        elif step == "quote":
            self.state["contact"] = text
            self.state["step"] = "done"
            return (
                "Perfect ✅ Our team will reach out shortly. "
                "Would you like to know how we work from idea to launch?"
            )

        # ---------- Conversation Done ----------
        elif step == "done":
            # allow restarting conversation if user greets again
            if text in ["hi", "hello", "hey"]:
                self.state = {"step": "get_name"}
                return "👋 Welcome back! What's your name?"

            if "yes" in text:
                return (
                    "We begin with requirement analysis 🧠 → design 🎨 → development 🧑‍💻 "
                    "→ testing 🧪 → deployment ☁️."
                )

            # reset for anything else
            self.state = {"step": "greet"}
            return (
                "Glad to help! If you’d like to start another enquiry, just say 'hello' 🚀"
            )

        # ---------- Fallback ----------
        return "I'm sorry, I didn't catch that — could you please rephrase?"

    # ---------- Helper: Quick Price Estimator ----------
    def estimate_price(self, project_text):
        project_text = project_text.lower()
        if "website" in project_text:
            return 800
        if "app" in project_text:
            return 2000
        if "automation" in project_text or "bot" in project_text:
            return 1000
        return 1200