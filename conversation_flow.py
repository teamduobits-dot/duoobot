# ----------------------------------------------------------
#  DuooBot — Smarter local logic edition
#  (multi‑TLD domain flow, no third‑party APIs)
# ----------------------------------------------------------
import socket
import re
import random
from datetime import datetime
from difflib import SequenceMatcher
from database import Lead, SessionLocal


# ----------------------------------------------------------
#  Helpers — lightweight “language understanding”
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
    """Simplify user text for flexible matching."""
    return re.sub(r"[^a-z0-9\s]+", "", txt.lower()).strip()


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def detect_category(text):
    """Try to identify category from generic phrasing."""
    low = normalize(text)
    for key, values in SYNONYMS.items():
        if key in ("yes", "no"):
            continue
        for v in values + [key]:
            if v in low or similarity(low, v) > 0.7:
                return key
    return "unknown"


def detect_yes_no(text):
    low = normalize(text)
    for k in ("yes", "no"):
        for v in SYNONYMS[k] + [k]:
            if v in low:
                return k
    return None


# ----------------------------------------------------------
#  Personality bits
# ----------------------------------------------------------
EMOJIS = ["🙂", "😄", "🚀", "✨", "👌", "🤖"]
GREETINGS = [
    "Hi {name}! Ready to build something creative?",
    "Hey {name}! Let's craft your next project.",
    "Hello {name}! Excited to start?",
]
THANKS = [
    "Perfect, got it!",
    "Awesome choice!",
    "Excellent!",
    "Cool 👍",
]
ERRORS = [
    "Oops, didn’t catch that.",
    "Hmm, could you rephrase that?",
    "Not sure I understood that one.",
]


# ----------------------------------------------------------
#  Conversation core
# ----------------------------------------------------------
class Conversation:
    def __init__(self, state=None, user_name=None):
        self.state = state or {"step": "project_type"}
        if user_name:
            self.state["name"] = user_name.split(" ")[0]
        self.state.setdefault("history", [])

    # ------------------------------------------------------
    # Main brain — reply generation
    # ------------------------------------------------------
    def reply(self, text: str):
        step = self.state.get("step", "project_type")
        text = text.strip()
        low = normalize(text)
        self.state["history"].append({"from": "user", "text": text})

        # allow topic jump to budget early
        if "budget" in low and step not in ("budget", "quote"):
            self.state["step"] = "budget"
            return {
                "text": "Sure! Let’s talk budget — what range do you have in mind?",
                "options": [],
            }

        # ---------- Step 1: Project Category ----------
        if step == "project_type":
            self.state["step"] = "subtype"
            user = self.state.get("name", "there")
            greet = random.choice(GREETINGS).format(name=user)
            emo = random.choice(EMOJIS)
            return {
                "text": f"{greet} {emo}\nWhat type of project do you need?",
                "options": ["Website", "App", "Automation", "Bot"],
            }

        # ---------- Step 2: Sub‑Type ----------
        elif step == "subtype":
            kind = detect_category(low)
            self.state["project"] = kind
            self.state["subtype"] = kind
            self.state["step"] = "features"

            if kind == "website":
                prompt = "Great! What type of website are you planning to build?"
                opts = ["Landing Page", "Portfolio", "E‑Commerce", "Corporate"]
            elif kind == "app":
                prompt = "Nice! Which core features would you want in your app?"
                opts = ["Login", "Payments", "AI", "Dashboard"]
            elif kind == "bot":
                prompt = "Bot! Love it 🤖 What should your bot be able to do?"
                opts = ["Chat", "Automation", "Support", "Integration"]
            else:
                prompt = (
                    "Sounds interesting! Which core features matter most to you?"
                )
                opts = ["Automation", "AI", "Integration", "Dashboard"]

            return {"text": prompt, "options": opts}

        # ---------- Step 3: Features ----------
        elif step == "features":
            feats = [
                f.strip().lower()
                for f in text.replace(" and ", ",").split(",")
                if f.strip()
            ]
            self.state["features"] = feats
            self.state["contains_payment"] = any("payment" in f for f in feats)
            self.state["step"] = "budget"
            pretty = ", ".join([f.title() for f in feats]) if feats else "no specific"
            thanks = random.choice(THANKS)
            return {
                "text": f"Got it 👌 Selected features: {pretty}. {thanks}\nNow, what’s your budget range (₹)?",
                "options": ["< 10 000", "10 – 30 k", "30 k +"],
            }

        # ---------- Step 4: Budget ----------
        elif step == "budget":
            self.state["budget"] = text
            self.state["step"] = "assets"
            return {
                "text": "Do you already have a logo and social media pages?",
                "options": ["Yes", "No"],
            }

        # ---------- Step 5: Assets ----------
        elif step == "assets":
            yesno = detect_yes_no(low)
            no_ans = yesno == "no"
            self.state["has_logo"] = not no_ans
            self.state["has_social"] = not no_ans
            self.state["step"] = "timeline"
            return {
                "text": "When are you planning to launch your project?",
                "options": ["1 – 2 Weeks", "1 Month", "Flexible"],
            }

        # ---------- Step 6: Timeline ----------
        elif step == "timeline":
            self.state["urgent"] = "week" in low or "soon" in low
            self.state["step"] = "domain_question"
            return {
                "text": "Do you already own a domain name (yes / no)?",
                "options": ["Yes", "No"],
            }

        # ---------- Step 7A: Domain question ----------
        elif step == "domain_question":
            answer = detect_yes_no(low)
            if answer == "yes":
                self.state["step"] = "domain_have"
                return {
                    "text": "Great! Please type your current domain (e.g. mybrand.com)",
                    "options": [],
                }
            elif answer == "no":
                self.state["step"] = "domain_check_offer"
                return {
                    "text": "Would you like to check if a domain is available for you?",
                    "options": ["Yes", "No"],
                }
            else:
                return {"text": "Please answer Yes or No 🙂", "options": []}

        # ---------- Step 7B: Offer domain check ----------
        elif step == "domain_check_offer":
            answer = detect_yes_no(low)
            if answer == "no":
                self.state["step"] = "quote"
                return {
                    "text": "No problem 🙂 We’ll skip domain checking and proceed.",
                    "options": [],
                }
            self.state["step"] = "domain_extension"
            return {
                "text": "Select which TLDs you’d like me to check:",
                "options": [".com", ".in", ".net", ".org", ".co"],
            }

        # ---------- Step 7C: Choose domain extensions ----------
        elif step == "domain_extension":
            tlds = [t for t in [".com", ".in", ".net", ".org", ".co"] if t in low]
            self.state["selected_tlds"] = tlds or [".com"]
            self.state["step"] = "domain_input"
            return {
                "text": f"Okay 👍 Please type your base domain name (e.g. aditya)",
                "options": [],
            }

        # ---------- Step 7D: Handle domain input ----------
        elif step == "domain_input":
            self.state["domain_base"] = re.sub(r"\s+", "", low)
            # frontend now performs actual check via /domaincheck
            self.state["step"] = "domain_result_wait"
            return {
                "text": "Got it ✅ Click ‘Check Availability’ to see which domains are open.",
                "options": [],
            }

        # ---------- Step 7E: After domain results shown ----------
        elif step == "domain_result_wait":
            self.state["step"] = "quote"
            return {
                "text": "Once you’ve reviewed your domain options, shall we continue to cost estimation?",
                "options": ["Yes", "No"],
            }

        # ---------- Step 8: Quote ----------
        elif step == "quote":
            if "no" in low:
                return {
                    "text": "Alright 🙂 We can skip the estimate for now. Type ‘Start New Project’ when ready.",
                    "options": [],
                }

            self.state["step"] = "done"
            cost = self.estimate_price_inr()
            summary = self.project_summary(cost)
            self.save_lead_to_db()

            extra = random.choice(THANKS)
            return {
                "text": f"{summary}\n\n💸 Estimated cost ≈ ₹ {cost:,} INR. {extra}\nOur team will reach out soon, {self.state.get('name','friend')}!",
                "options": ["Start New Project"],
            }

        # ---------- Restart ----------
        elif step == "done":
            if any(word in low for word in ("start", "new", "again", "hello")):
                name = self.state.get("name")
                self.state = {"step": "project_type", "name": name, "history": []}
                return {
                    "text": "Let's start over and plan a new project!",
                    "options": ["Website", "App", "Automation", "Bot"],
                }
            return {"text": "Type 'Start New Project' to begin again.", "options": []}

        # ---------- Fallback ----------
        return {"text": random.choice(ERRORS), "options": []}

    # ----------------------------------------------------------
    # Check domain (lightweight DNS probe)
    # ----------------------------------------------------------
    def check_domain(self, domain_name: str) -> bool:
        try:
            socket.gethostbyname(domain_name)
            return False
        except socket.gaierror:
            return True

    # ----------------------------------------------------------
    # Estimate cost logic (tiny heuristic)
    # ----------------------------------------------------------
    def estimate_price_inr(self):
        proj = self.state.get("project", "")
        sub = self.state.get("subtype", "")
        base_table = {
            "landing": 4000,
            "portfolio": 8000,
            "e‑commerce": 25000,
            "app": 50000,
            "automation": 15000,
            "bot": 12000,
            "website": 10000,
        }
        base = next((p for k, p in base_table.items() if k in proj or k in sub), 8000)

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

        # Assets, urgency adjustments
        if not self.state.get("has_logo", True):
            addons += 2000
        if not self.state.get("has_social", True):
            addons += 1500
        if self.state.get("urgent"):
            base = int(base * 1.1)

        return base + addons

    # ----------------------------------------------------------
    # Summary string
    # ----------------------------------------------------------
    def project_summary(self, total):
        domain = self.state.get("domain_base") or self.state.get("domain_name")
        mark = ""
        if domain:
            mark = "✅" if self.state.get("domain_available") else "❌"
            domain = f" | Domain {mark} {domain}"
        return (
            f"📋 Summary for {self.state.get('name','Client')}: "
            f"{self.state.get('project','project')} project ≈ ₹ {total:,} INR {domain}"
        )

    # ----------------------------------------------------------
    # Save Lead into SQLite
    # ----------------------------------------------------------
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
                domain_name=self.state.get("domain_base")
                or self.state.get("domain_name"),
                domain_available="yes" if self.state.get("domain_available") else "no",
                estimated_cost=f"₹ {self.estimate_price_inr():,}",
            )
            session.add(lead)
            session.commit()
        except Exception as err:
            print(f"❌ Error saving lead: {err}")
        finally:
            session.close()