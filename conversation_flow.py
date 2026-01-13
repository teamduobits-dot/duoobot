# ----------------------------------------------------------
#  DuooBot — Conversational Logic v2 (smarter & friendlier)
# ----------------------------------------------------------
import socket
import re
import random
from difflib import SequenceMatcher
from database import Lead, SessionLocal

# ----------------------------------------------------------
#  Simple NLP helpers
# ----------------------------------------------------------
SYNONYMS = {
    "website": ["web", "site", "page", "store", "landing", "portfolio", "shop"],
    "app": ["application", "mobile", "android", "ios", "software"],
    "bot": ["assistant", "chatbot", "automation"],
    "automation": ["auto", "script", "process"],
    "yes": ["ok", "sure", "yep", "alright", "yeah"],
    "no": ["nope", "none", "nah", "never"],
}

def normalize(txt: str) -> str:
    return re.sub(r"[^a-z0-9\s]+", "", txt.lower()).strip()

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def detect_category(text):
    t = normalize(text)
    for key, vals in SYNONYMS.items():
        if key in ("yes", "no"): 
            continue
        for v in vals + [key]:
            if v in t or similarity(t, v) > 0.7:
                return key
    return "unknown"

def detect_yes_no(text):
    t = normalize(text)
    for k in ("yes", "no"):
        for v in SYNONYMS[k] + [k]:
            if v in t:
                return k
    return None

# ----------------------------------------------------------
#  Conversational personality
# ----------------------------------------------------------
GREETINGS = [
    "Hi {name}! 👋 Excited to build something special together?",
    "Hey {name}! 🌟 Ready to bring your idea to life?",
    "Welcome {name}! 🚀 What shall we create today?",
]
THANKS = [
    "Perfect, that helps a lot!",
    "Great choice!",
    "Awesome 👍",
    "Got it — thanks!",
]
CONFIRM = [
    "Sounds good!",
    "Nice one.",
    "Cool — noted.",
]
ERRORS = [
    "Hmm, could you rephrase that?",
    "I’m not sure I got that. Could you clarify?",
    "Oops — that went over my circuits 😅. Try again?",
]
EMOJIS = ["🙂","😄","🚀","✨","🤖"]

# ----------------------------------------------------------
#  Conversation Core
# ----------------------------------------------------------
class Conversation:
    def __init__(self, state=None, user_name=None):
        self.state = state or {"step": "project_type"}
        if user_name:
            self.state["name"] = user_name.split(" ")[0]
        self.state.setdefault("history", [])

    # ------------------------------------------------------
    def reply(self, text: str):
        step = self.state.get("step", "project_type")
        low = normalize(text)
        self.state["history"].append({"from": "user", "text": text.strip()})

        # allow immediate jump to budget
        if "budget" in low and step not in ("budget", "quote"):
            self.state["step"] = "budget"
            return {
                "text": "Sure! Let’s talk budget — what price range were you thinking of?",
                "options": ["< 10 000", "10 – 30 k", "30 k +"],
            }

        # ---------- Step 1: Greeting / Project type ----------
        if step == "project_type":
            self.state["step"] = "subtype"
            user = self.state.get("name", "there")
            greet = random.choice(GREETINGS).format(name=user)
            return {
                "text": f"{greet}\nWhat type of project would you like to start?",
                "options": ["Website", "App", "Automation", "Bot"],
            }

        # ---------- Step 2: Sub‑type ----------
        elif step == "subtype":
            kind = detect_category(low)
            self.state["project"] = self.state["subtype"] = kind
            self.state["step"] = "features"

            if kind == "website":
                text = "Awesome! What kind of website are you planning?"
                opts = ["Landing Page", "Portfolio", "E‑Commerce", "Corporate"]
            elif kind == "app":
                text = "Nice! Which key features would your app need?"
                opts = ["Login", "Payments", "AI", "Dashboard"]
            elif kind == "bot":
                text = "Bots are fun 🤖 What tasks should your bot handle?"
                opts = ["Chat", "Automation", "Support", "Integration"]
            else:
                text = "Got it! Which features matter most for your project?"
                opts = ["Automation", "AI", "Integration", "Dashboard"]

            return {"text": text, "options": opts}

        # ---------- Step 3: Features ----------
        elif step == "features":
            feats = [f.strip().lower() for f in text.replace(" and ", ",").split(",") if f.strip()]
            self.state["features"] = feats
            self.state["contains_payment"] = any("payment" in f for f in feats)
            self.state["step"] = "budget"
            pretty = ", ".join([f.title() for f in feats]) if feats else "none selected"
            return {
                "text": f"Got it 👌 Features: {pretty}. {random.choice(THANKS)}\nWhat's your approximate budget (₹)?",
                "options": ["< 10 000", "10 – 30 k", "30 k +"],
            }

        # ---------- Step 4: Budget ----------
        elif step == "budget":
            self.state["budget"] = text
            self.state["step"] = "assets"
            return {
                "text": "Do you already have a logo and social media profiles we can use?",
                "options": ["Yes", "No"],
            }

        # ---------- Step 5: Assets ----------
        elif step == "assets":
            yn = detect_yes_no(low)
            self.state["has_logo"] = self.state["has_social"] = not (yn == "no")
            self.state["step"] = "timeline"
            return {
                "text": "Cool! When are you hoping to launch your project?",
                "options": ["1 – 2 Weeks", "1 Month", "Flexible"],
            }

        # ---------- Step 6: Timeline ----------
        elif step == "timeline":
            self.state["urgent"] = "week" in low or "soon" in low
            self.state["step"] = "domain_question"
            return {
                "text": "Do you already own a domain name?",
                "options": ["Yes", "No"],
            }

        # ---------- Step 7: Domain ownership ----------
        elif step == "domain_question":
            ans = detect_yes_no(low)
            if ans == "yes":
                self.state["step"] = "domain_have"
                return {"text": "Great! Please type your current domain (e.g. mybrand.com)."}
            elif ans == "no":
                self.state["step"] = "domain_check_offer"
                return {
                    "text": "Would you like me to help check if a domain is available?",
                    "options": ["Yes", "No"],
                }
            return {"text": "Just need a Yes or No 🙂", "options": []}

        # ---------- Step 8: Offer domain check ----------
        elif step == "domain_check_offer":
            ans = detect_yes_no(low)
            if ans == "no":
                self.state["step"] = "quote"
                return {"text": "No problem 🙂 We’ll skip that and move ahead."}
            self.state["step"] = "domain_extension"
            return {
                "text": "Select the extensions you’d like to check:",
                "options": [".com", ".in", ".net", ".org", ".co"],
            }

        # ---------- Step 9: TLD selection ----------
        elif step == "domain_extension":
            tlds = [t for t in [".com", ".in", ".net", ".org", ".co"] if t in low]
            self.state["selected_tlds"] = tlds or [".com"]
            self.state["step"] = "domain_input"
            return {"text": "Great! Type the base name you want (e.g. aditya)."}

        # ---------- Step 10: Domain input ----------
        elif step == "domain_input":
            self.state["domain_base"] = re.sub(r"\s+", "", low)
            self.state["step"] = "domain_result_wait"
            return {"text": "Got it ✅ Click ‘Check Availability’ to see which domains are free."}

        # ---------- Step 11: Post-domain results ----------
        elif step == "domain_result_wait":
            self.state["step"] = "quote"
            return {
                "text": "Seen your options? Shall we continue to a quick cost estimate?",
                "options": ["Yes", "No"],
            }

        # ---------- Step 12: Quote ----------
        elif step == "quote":
            if "no" in low:
                return {"text": "Alright 🙂 We can skip the estimate for now. Type ‘Start New Project’ whenever you’re ready."}
            cost = self.estimate_price_inr()
            summary = self.project_summary(cost)
            self.save_lead_to_db()
            self.state["step"] = "done"
            return {
                "text": f"{summary}\n💸 Estimated cost ≈ ₹ {cost:,}\n{random.choice(THANKS)} We’ll get in touch soon, {self.state.get('name','friend')}!",
                "options": ["Start New Project"],
            }

        # ---------- Restart ----------
        elif step == "done":
            if any(k in low for k in ("start", "new", "again", "hello")):
                name = self.state.get("name")
                self.state = {"step": "project_type", "name": name, "history": []}
                return {"text": "Let’s plan a new project 🎯 What kind would you like?", "options": ["Website","App","Automation","Bot"]}
            return {"text": "Type ‘Start New Project’ to begin again.", "options": []}

        # ---------- Fallback ----------
        return {"text": random.choice(ERRORS), "options": []}

    # ----------------------------------------------------------
    # Utility helpers
    # ----------------------------------------------------------
    def check_domain(self, domain_name: str) -> bool:
        try:
            socket.gethostbyname(domain_name)
            return False
        except socket.gaierror:
            return True

    def estimate_price_inr(self):
        proj = self.state.get("project","")
        sub = self.state.get("subtype","")
        base_vals = {
            "landing": 4000,"portfolio": 8000,"e‑commerce": 25000,
            "app": 50000,"automation": 15000,"bot": 12000,"website": 10000,
        }
        base = next((p for k,p in base_vals.items() if k in proj or k in sub), 8000)

        feats = self.state.get("features",[])
        addons = 0
        for f in feats:
            f = f.lower()
            if "login" in f: addons += 1500
            if "payment" in f: addons += 2500
            if "ai" in f: addons += 4000
            if "dashboard" in f: addons += 3000
        if not self.state.get("has_logo",True): addons += 2000
        if not self.state.get("has_social",True): addons += 1500
        if self.state.get("urgent"): base = int(base * 1.1)
        return base + addons

    def project_summary(self, total):
        domain = self.state.get("domain_base") or self.state.get("domain_name")
        tag = ""
        if domain:
            mark = "✅" if self.state.get("domain_available") else "❌"
            tag = f" | Domain {mark} {domain}"
        return f"📋 Summary for {self.state.get('name','Client')}: {self.state.get('project','project')} project ≈ ₹ {total:,} INR{tag}"

    def save_lead_to_db(self):
        try:
            session = SessionLocal()
            lead = Lead(
                name=self.state.get("name"),
                project=self.state.get("project"),
                details=str(self.state.get("features")),
                budget=self.state.get("budget"),
                contact=self.state.get("contact"),
                has_logo=self.state.get("has_logo"),
                has_social=self.state.get("has_social"),
                contains_payment=self.state.get("contains_payment"),
                urgent=self.state.get("urgent"),
                domain_name=self.state.get("domain_base") or self.state.get("domain_name"),
                domain_available="yes" if self.state.get("domain_available") else "no",
                estimated_cost=f"₹ {self.estimate_price_inr():,}",
            )
            session.add(lead)
            session.commit()
        except Exception as err:
            print(f"❌ Error saving lead: {err}")
        finally:
            session.close()