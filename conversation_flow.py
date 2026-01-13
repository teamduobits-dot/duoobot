# ----------------------------------------------------------
#  DuooBot — Conversational Logic v5 (Deep Hierarchical Flow)
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
#  Personality text pools
# ----------------------------------------------------------
GREETINGS = [
    "Hi {name}! 👋 Excited to build something special together?",
    "Hey {name}! 🌟 Ready to bring your idea to life?",
    "Welcome {name}! 🚀 What shall we create today?",
]
THANKS = ["Perfect, that helps a lot!", "Great choice!", "Awesome 👍", "Got it — thanks!"]
ERRORS = [
    "Hmm, could you rephrase that?",
    "I’m not sure I got that. Could you clarify?",
    "Oops — that went over my circuits 😅. Try again?",
]

# ----------------------------------------------------------
#  Structured Question Bank (v5 Tree)
# ----------------------------------------------------------
QUESTION_TREE = {
    "website": {
        "landing": [
            {"q": "What kind of landing page are you planning?", "options": ["Single Page", "Multi‑page", "Promo/Product"]},
            {"q": "Do you need form integrations (lead collection)?", "options": ["Yes", "No"]},
            {"q": "Goal of the page?", "options": ["Sales", "Newsletter", "Signup", "Event"]},
        ],
        "portfolio": [
            {"q": "For business or personal brand?", "options": ["Business", "Personal", "Agency"]},
            {"q": "Include a blog or case studies?", "options": ["Yes", "No"]},
            {"q": "Upload new projects manually or via CMS?", "options": ["Manual", "CMS", "API"]},
        ],
        "e‑commerce": [
            {"q": "Expected number of products?", "options": ["1‑50", "50‑500", "500+"]},
            {"q": "Preferred payment gateway?", "options": ["Stripe", "Razorpay", "PayPal", "Other"]},
            {"q": "Inventory management integration?", "options": ["Yes", "No"]},
        ],
        "corporate": [
            {"q": "Internal employee/intranet portal needed?", "options": ["Yes", "No"]},
            {"q": "Careers section with job posts?", "options": ["Yes", "No"]},
            {"q": "Multi‑language support?", "options": ["Yes", "No"]},
        ],
    },
    "app": [
        {"q": "Which platforms are you targeting?", "options": ["Android", "iOS", "Web", "All"]},
        {"q": "Who will use this app?", "options": ["Customers", "Staff", "Partners"]},
        {"q": "Key features?", "options": ["Login", "Payments", "Notifications", "AI", "Dashboard"]},
        {"q": "Need backend admin panel?", "options": ["Yes", "No"]},
    ],
    "automation": [
        {"q": "What process do you want automated?", "options": ["Reports", "APIs", "Mailing", "Workflows", "Monitoring"]},
        {"q": "Current tool or method used?", "options": ["Excel", "CRM", "ERP", "Manual"]},
        {"q": "Goal of automation?", "options": ["Save time", "Reduce errors", "Integrate systems"]},
        {"q": "Trigger frequency?", "options": ["Daily", "Weekly", "On demand"]},
    ],
    "bot": [
        {"q": "What’s the primary purpose of this bot?", "options": ["Customer Support", "Lead Capture", "Internal FAQ", "Booking Assistant"]},
        {"q": "Preferred tone/personality?", "options": ["Professional", "Friendly", "Playful"]},
        {"q": "Where should it be deployed?", "options": ["Website", "WhatsApp", "Telegram", "Slack"]},
    ],
}

COMMON_FLOW = [
    {"q": "Who is your target audience?", "options": []},
    {"q": "What’s the main goal?", "options": ["Sales", "Leads", "Branding", "Automation"]},
    {"q": "Do you already have a logo or branding assets?", "options": ["Yes", "No"]},
    {"q": "When are you hoping to launch your project?", "options": ["1‑2 Weeks", "1 Month", "Flexible"]},
    {"q": "Do you already own a domain name?", "options": ["Yes", "No"]},
]

# ----------------------------------------------------------
#  Conversation Core
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

        # 2️⃣ Project Selection
        elif step == "project_type":
            category = detect_category(low)
            self.state["project"] = category
            
            if category == "website":
                self.state["step"] = "website_subtype"
                return {
                    "text": "Nice! What type of website are you planning?",
                    "options": ["Landing", "Portfolio", "E‑Commerce", "Corporate"]
                }
            elif category in ["app", "automation", "bot"]:
                self.state["step"] = "category_questions"
                self.state["q_index"] = 0
                first_q = QUESTION_TREE[category][0]
                return {"text": first_q["q"], "options": first_q["options"]}
            else:
                # fallback if unknown
                return {"text": "Could you clarify? (Website, App, Automation, Bot)", "options": ["Website", "App", "Automation", "Bot"]}

        # 3️⃣ Website Subtype
        elif step == "website_subtype":
            # flexible mapping for subtype choice
            sub = "landing"
            if "landing" in low: sub = "landing"
            elif "portfolio" in low: sub = "portfolio"
            elif "commerce" in low: sub = "e‑commerce"
            elif "corporate" in low: sub = "corporate"
            
            self.state["subtype"] = sub
            self.state["step"] = "category_questions"
            self.state["q_index"] = 0
            
            first_q = QUESTION_TREE["website"][sub][0]
            return {"text": first_q["q"], "options": first_q["options"]}

        # 4️⃣ Category-Specific Questions Loop
        elif step == "category_questions":
            cat = self.state["project"]
            sub = self.state.get("subtype")
            idx = self.state.get("q_index", 0)

            # Store answer
            self.state[f"cat_q_{idx}"] = text
            
            next_idx = idx + 1
            self.state["q_index"] = next_idx

            # Determine list of questions
            if cat == "website":
                q_list = QUESTION_TREE["website"][sub]
            else:
                q_list = QUESTION_TREE[cat]

            if next_idx < len(q_list):
                nxt = q_list[next_idx]
                return {"text": nxt["q"], "options": nxt["options"]}
            
            # Finished specific questions -> go to Common Flow
            self.state["step"] = "common_questions"
            self.state["c_index"] = 0
            first_c = COMMON_FLOW[0]
            return {"text": first_c["q"], "options": first_c["options"]}

        # 5️⃣ Common Questions Loop
        elif step == "common_questions":
            c_idx = self.state.get("c_index", 0)
            self.state[f"common_q_{c_idx}"] = text
            
            # Special check for "Domain" question (index 4 in COMMON_FLOW)
            if c_idx == 4:
                yn = detect_yes_no(low)
                self.state["has_domain"] = yn == "yes"
                if yn == "yes":
                    self.state["step"] = "domain_input"
                    return {"text": "Great! Please type your domain (e.g. mybrand.com)."}
                else:
                    self.state["step"] = "summary"
                    return self.generate_final_summary()

            self.state["c_index"] = c_idx + 1
            next_c = c_idx + 1

            if next_c < len(COMMON_FLOW):
                nxt = COMMON_FLOW[next_c]
                return {"text": nxt["q"], "options": nxt["options"]}
            
            # If loop finished naturally
            self.state["step"] = "summary"
            return self.generate_final_summary()

        # 6️⃣ Domain Input
        elif step == "domain_input":
            self.state["domain_name"] = text
            self.state["step"] = "summary"
            return self.generate_final_summary()

        # 7️⃣ Summary
        elif step == "summary":
            pass 

        # 🔁 Restart Logic
        if any(k in low for k in ("start", "new", "again", "hello")):
            name = self.state.get("name")
            self.state = {"step": "greeting", "name": name, "history": []}
            return self.reply("hello")

        return {"text": "Type 'Start New Project' to begin again 🎯", "options": ["Start New Project"]}

    # ----------------------------------------------------------
    #  Helper to generate summary
    # ----------------------------------------------------------
    def generate_final_summary(self):
        cost = self.estimate_price_inr()
        summary = self.project_summary(cost)
        self.save_lead_to_db()
        self.state["step"] = "done"
        return {
            "text": (
                f"{summary}\n"
                f"💸 Estimated cost ≈ ₹ {cost:,}\n"
                "Thanks for sharing details! We'll be in touch.\n"
                "Type 'Start New Project' to begin again."
            ),
            "options": ["Start New Project"]
        }

    # ----------------------------------------------------------
    #  Utility: Domain Check
    # ----------------------------------------------------------
    def check_domain(self, domain_name: str) -> bool:
        try:
            socket.gethostbyname(domain_name)
            return False
        except socket.gaierror:
            return True

    # ----------------------------------------------------------
    #  Utility: Price Estimation
    # ----------------------------------------------------------
    def estimate_price_inr(self):
        proj = self.state.get("project", "")
        base = 8000
        # Simple base pricing
        if proj == "app": base = 50000
        elif proj == "bot": base = 12000
        elif proj == "automation": base = 15000
        elif "e‑commerce" in str(self.state.get("subtype","")): base = 25000
        elif "landing" in str(self.state.get("subtype","")): base = 4000
        
        # Additive logic based on keywords in history
        history_str = str(self.state).lower()
        addons = 0
        if "login" in history_str: addons += 1500
        if "payment" in history_str: addons += 2500
        if "ai" in history_str: addons += 4000
        if "dashboard" in history_str: addons += 3000
        if "cms" in history_str: addons += 5000
        
        # urgent? (checked in common questions)
        urgent = "week" in str(self.state.get("common_q_3", "")).lower()
        if urgent:
            base = int(base * 1.15)

        return base + addons

    # ----------------------------------------------------------
    #  Utility: Summary Text
    # ----------------------------------------------------------
    def project_summary(self, total):
        domain = self.state.get("domain_name", "")
        tag = f" | Domain: {domain}" if domain else ""
        
        proj_name = self.state.get("subtype") or self.state.get("project")
        audience = self.state.get("common_q_0", "General")
        goal = self.state.get("common_q_1", "General")
        
        return (
            f"📋 Summary for {self.state.get('name', 'Client')}:\n"
            f"• Project: {str(proj_name).title()}\n"
            f"• Target: {audience}\n"
            f"• Goal: {goal}\n"
            f"{tag}"
        )

    # ----------------------------------------------------------
    #  Utility: Save to DB
    # ----------------------------------------------------------
    def save_lead_to_db(self):
        try:
            session = SessionLocal()
            lead = Lead(
                name=self.state.get("name"),
                project=self.state.get("project"),
                details=str(self.state), # storing full state dump for deep context
                budget=self.state.get("common_q_2"), # approximate mapping
                contact=self.state.get("contact"),
                has_logo="yes" in str(self.state.get("common_q_2","")).lower(),
                urgent="week" in str(self.state.get("common_q_3","")).lower(),
                domain_name=self.state.get("domain_name"),
                estimated_cost=f"₹ {self.estimate_price_inr():,}",
            )
            session.add(lead)
            session.commit()
        except Exception as err:
            print(f"❌ Error saving lead: {err}")
        finally:
            session.close()