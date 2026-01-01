class Conversation:
    def __init__(self, state=None):
        self.state = state or {"step": "greet"}

    def reply(self, text: str):
        step = self.state["step"]
        text = text.lower().strip()

        if step == "greet":
            self.state["step"] = "get_name"
            return "👋 Hi! I'm DuooBot — your tech assistant at DuooBits. What's your name?"

        elif step == "get_name":
            self.state["name"] = text.title()
            self.state["step"] = "project_type"
            return f"Nice to meet you, {self.state['name']}! What kind of project are you planning — website, app or automation?"

        elif step == "project_type":
            self.state["project"] = text
            self.state["step"] = "details"
            return f"Great — a {self.state['project']}! Could you tell me the main features you need?"

        elif step == "details":
            self.state["details"] = text
            self.state["step"] = "quote"
            cost = self.estimate_price(text)
            return f"Understood. Your starting estimate is around ${cost}. Would you like to share your contact email so we can follow up?"

        elif step == "quote":
            self.state["contact"] = text
            self.state["step"] = "done"
            return "Perfect ✅ Our team will reach out shortly. Would you like to know how we work from idea to launch?"

        elif step == "done":
            if "yes" in text:
                return "We begin with analysis 🧠 → design 🎨 → development 🧑‍💻 → testing 🧪 → deployment ☁️."
            return "Glad to help! DuooBits is here whenever you need smart software solutions 🚀"

        return "I'm sorry, I didn't catch that."

    def estimate_price(self, project_text):
        if "website" in project_text:
            return 800
        if "app" in project_text:
            return 2000
        if "automation" in project_text or "bot" in project_text:
            return 1000
        return 1200