# ----------------------------------------------------------
#  DuooBot — Conversational Logic v4 (context‑aware smart flow)
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
ERRORS = [
    "Hmm, could you rephrase that?",
    "I’m not sure I got that. Could you clarify?",
    "Oops — that went over my circuits 😅. Try again?",
]

# ----------------------------------------------------------
#  Conversation Core (v4)
# ----------------------------------------------------------
class Conversation:
    def __init__(self, state=None, user_name=None):
        self.state = state or {"step": "greeting"}
        if user_name:
            self.state["name"] = user_name.split(" ")[0]
        self.state.setdefault("history", [])

    # ------------------------------------------------------
    def reply(self, text: str):
        step = self.state.get("step", "greeting")
        low = normalize(text)
        self.state["history"].append({"from": "user", "text": text.strip()})

        # 1️⃣ Greeting
        if step == "greeting":
            self.state["step"] = "project_type"
            user = self.state.get("name", "friend")
            greet = random.choice(GREETINGS).format(name=user)
            return {
                "text": f"{greet}\nWhat kind of project would you like to start?",
                "options": ["Website", "App", "Automation", "Bot"],
            }

        # 2️⃣ Project type
        elif step == "project_type":
            cat = detect_category(low)
            self.state["project"] = cat
            self.state["step"] = "audience"
            return {
                "text": "Great! Could you tell me who this project is mainly for — your customers, internal team, or a specific market?",
                "options": [],
            }

        # 3️⃣ Audience context
        elif step == "audience":
            self.state["audience"] = text
            self.state["step"] = "goal"
            return {
                "text": "Good to know 👌 And what’s your main goal with this project — sales, leads, branding, or automation?",
                "options": ["Sales", "Leads", "Branding", "Automation", "Other"],
            }

        # 4️⃣ Goal context
        elif step == "goal":
            self.state["goal"] = text
            self.state["step"] = "features"

            proj = self.state.get("project", "")
            if proj == "website":
                msg = "Nice! What type of website are you planning?"
                opts = ["Landing Page", "Portfolio", "E‑Commerce", "Corporate"]
            elif proj == "app":
                msg = "Awesome! Which core features should your app include?"
                opts = ["Login", "Payments", "AI", "Dashboard"]
            elif proj == "bot":
                msg = "Bots are fun 🤖 What should it do for your business?"
                opts = ["Chat", "Automation", "Support", "Integration"]
            elif proj == "automation":
                msg = "Great! What processes do you want automated?"
                opts = ["Reports", "APIs", "Workflows", "Data Entry"]
            else:
                msg = "Got it! Tell me the key features you need."
                opts = ["Login", "Payments", "Dashboard", "AI"]

            return {"text": msg, "options": opts}

        # 5️⃣ Features
        elif step == "features":
            feats = [x.strip() for x in text.replace(" and ", ",").split(",") if x.strip()]
            self.state["features"] = feats
            self.state["contains_payment"] = any("payment" in f.lower() for f in feats)
            self.state["step"] = "budget"
            feat_list = ", ".join(feats) if feats else "none"
            return {
                "text": f"Got it 👌 Features: {feat_list}. What's your budget range (₹)?",
                "options": ["< 10 000", "10 – 30 k", "30 k +"],
            }

        # 6️⃣ Budget (context aware)
        elif step == "budget":
            self.state["budget"] = text
            self.state["step"] = "assets"

            budget_text = text.replace(" ", "").lower()
            if "<" in budget_text or "10" in budget_text:
                msg = "We'll focus on essential features to keep it efficient and cost‑friendly."
            elif "30" in budget_text:
                msg = "Nice, that gives flexibility to include quality design and smoother UX."
            else:
                msg = "Perfect! We'll tailor high‑end performance and branding for you."
            return {
                "text": f"{msg}\nDo you already have a logo or other branding assets?",
                "options": ["Yes", "No"],
            }

        # 7️⃣ Assets / Branding
        elif step == "assets":
            yn = detect_yes_no(low)
            self.state["has_logo"] = yn == "yes"
            self.state["has_social"] = self.state["has_logo"]
            self.state["needs_design"] = yn == "no"
            self.state["step"] = "timeline"
            note = ""
            if yn == "no":
                note = "\nNo worries — our creative team can help design your logo too."
            return {
                "text": f"When are you hoping to launch your project?{note}",
                "options": ["1‑2 Weeks", "1 Month", "Flexible"],
            }

        # 8️⃣ Timeline
        elif step == "timeline":
            self.state["timeline"] = text
            self.state["urgent"] = "week" in low or "soon" in low
            self.state["step"] = "domain"
            if self.state["urgent"]:
                extra = "Got it 🚀 We'll treat this as a priority build."
            else:
                extra = "Perfect timing — we can plan a steady rollout."
            return {
                "text": f"{extra}\nDo you already own a domain name?",
                "options": ["Yes", "No"],
            }

        # 9️⃣ Domain
        elif step == "domain":
            ans = detect_yes_no(low)
            self.state["has_domain"] = ans == "yes"
            self.state["step"] = "summary"
            if ans == "yes":
                return {"text": "Great! Please type your domain (e.g. mybrand.com)."}
            return {
                "text": "No problem 🙂 We can help you choose one later. Ready to view your project summary?",
                "options": ["Yes"],
            }

        # 🔟 Summary / Quote
        elif step == "summary":
            cost = self.estimate_price_inr()
            summary = self.project_summary(cost)
            self.save_lead_to_db()
            self.state["step"] = "done"
            return {
                "text": (
                    f"{summary}\n💸 Estimated cost ≈ ₹ {cost:,}\n"
                    "Thanks for sharing such detailed info! "
                    "Type 'Start New Project' to begin again."
                ),
                "options": ["Start New Project"],
            }

        # 🔁 Restart
        elif step == "done":
            if any(k in low for k in ("start", "new", "again", "hello")):
                name = self.state.get("name")
                self.state = {"step": "greeting", "name": name, "history": []}
                return self.reply("hello")
            return {"text": "Type 'Start New Project' to begin again 🎯"}

        # fallback safeguard
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
        proj = self.state.get("project", "")
        base_vals = {
            "landing": 4000,
            "portfolio": 8000,
            "e‑commerce": 25000,
            "website": 10000,
            "app": 50000,
            "automation": 15000,
            "bot": 12000,
        }
        base = next((p for k, p in base_vals.items() if k in proj), 8000)

        feats = self.state.get("features", [])
        addons = 0
        for f in feats:
            f = f.lower()
            if "login" in f:
                addons += 1500
            if "payment" in f:
                addons += 2500
            if "ai" in f:
                addons += 4000
            if "dashboard" in f:
                addons += 3000
        if not self.state.get("has_logo", True):
            addons += 2000
        if not self.state.get("has_social", True):
            addons += 1500
        if self.state.get("urgent"):
            base = int(base * 1.1)
        return base + addons

    def project_summary(self, total):
        domain = self.state.get("domain_name") or self.state.get("domain_base")
        tag = ""
        if domain:
            mark = "✅" if self.state.get("domain_available") else "❌"
            tag = f" | Domain {mark} {domain}"
        parts = []
        if self.state.get("audience"):
            parts.append(f"Audience: {self.state['audience']}")
        if self.state.get("goal"):
            parts.append(f"Goal: {self.state['goal']}")
        if self.state.get("needs_design"):
            parts.append("Includes logo/branding design")
        context = "\n— ".join(parts)
        return (
            f"📋 Summary for {self.state.get('name', 'Client')}: "
            f"{self.state.get('project', 'project')} project ≈ ₹ {total:,} INR{tag}\n"
            f"— {context if context else ''}"
        )

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
                domain_name=self.state.get("domain_name")
                or self.state.get("domain_base"),
                domain_available="yes"
                if self.state.get("domain_available")
                else "no",
                estimated_cost=f"₹ {self.estimate_price_inr():,}",
            )
            session.add(lead)
            session.commit()
        except Exception as err:
            print(f"❌ Error saving lead: {err}")
        finally:
            session.close()