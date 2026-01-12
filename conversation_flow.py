# conversation_flow.py
import socket
from datetime import datetime
from database import Lead, SessionLocal


class Conversation:
    def __init__(self, state=None):
        # Conversation context (persisted between messages)
        self.state = state or {"step": "greet"}

    # ----------------------------------------------------------
    # Generate reply based on current step and user message
    # ----------------------------------------------------------
    def reply(self, text: str):
        step = self.state.get("step", "greet")
        text = text.strip()
        low = text.lower()

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
                "What kind of project are you planning — landing page, full website, app, or automation?"
            )

        # ---------- Project Type ----------
        elif step == "project_type":
            self.state["project"] = low
            self.state["step"] = "budget"
            return (
                f"Great — a {self.state['project']} project! "
                "What's your budget range (under ₹10 000 / ₹10 – 30 k / ₹30 k+)?"
            )

        # ---------- Budget ----------
        elif step == "budget":
            self.state["budget"] = text
            self.state["step"] = "assets"
            return (
                "Do you already have a logo and social‑media accounts for your business (yes / no)?"
            )

        # ---------- Assets (logo / social) ----------
        elif step == "assets":
            self.state["has_logo"] = not ("no" in low)
            self.state["has_social"] = not ("no" in low)
            self.state["step"] = "features"
            return (
                "Nice! Could you list main features you’d like (login, payments, AI, dashboard …)?"
            )

        # ---------- Feature List ----------
        elif step == "features":
            self.state["contains_payment"] = "payment" in low or "checkout" in low
            self.state["details"] = text
            self.state["step"] = "timeline"
            return "Got it 💡 Do you have a deadline or launch date in mind?"

        # ---------- Timeline / Deadline ----------
        elif step == "timeline":
            self.state["urgent"] = any(k in low for k in ["week", "soon", "urgent"])
            self.state["step"] = "domain"
            return (
                "Almost done! Do you already own a domain name (yes / no)? "
                "If not, I can check availability for you – please type a domain (e.g., duobits.in)"
            )

        # ---------- Domain name / Checker ----------
        elif step == "domain":
            domain = low.replace(" ", "")
            self.state["domain_name"] = domain
            available = self.check_domain(domain)
            self.state["domain_available"] = available
            self.state["step"] = "quote"
            status = "✅ available" if available else "❌ already taken"
            return (
                f"The domain ‘{domain}’ is {status}.\n"
                f"{self.make_estimate_message()}\n\n"
                "Would you like to share your contact email so we can follow up?"
            )

        # ---------- Contact / Quote ----------
        elif step == "quote":
            self.state["contact"] = text
            self.state["step"] = "done"

            # Save to the SQLite database
            self.save_lead_to_db()

            summary = self.project_summary()
            return (
                f"Perfect ✅ Thanks {self.state.get('name','there')}!\n"
                f"{summary}\n"
                "Our team will reach out soon.\n"
                "Type 'hello' to start a new project 🚀"
            )

        # ---------- Conversation Done ----------
        elif step == "done":
            if low in ["hi", "hello", "hey"]:
                self.state = {"step": "get_name"}
                return "👋 Welcome back! What's your name?"
            return "If you’d like to describe a new project, just say ‘hello’. 🚀"

        # ---------- Fallback ----------
        return "🤖 Sorry, I didn’t catch that — could you rephrase please?"

    # ----------------------------------------------------------
    # Domain checker (free, socket‑based)
    # ----------------------------------------------------------
    def check_domain(self, domain_name: str) -> bool:
        try:
            socket.gethostbyname(domain_name)
            return False   # DNS exists → taken
        except socket.gaierror:
            return True    # No DNS record → probably available

    # ----------------------------------------------------------
    # Estimate price in INR using simple rule table
    # ----------------------------------------------------------
    def estimate_price_inr(self):
        proj = self.state.get("project", "")
        base_table = {
            "landing": (3000, 5000),
            "website": (8000, 15000),
            "ecommerce": (18000, 35000),
            "app": (40000, 80000),
            "automation": (10000, 25000),
        }

        base = 8000
        for key, rng in base_table.items():
            if key in proj:
                base = sum(rng) // 2

        addons = 0
        if not self.state.get("has_logo", True):
            addons += 2000
        if not self.state.get("has_social", True):
            addons += 1500
        if self.state.get("contains_payment"):
            addons += 2500
        if self.state.get("urgent"):
            addons = int(addons * 1.15)

        total = base + addons
        return total

    # ----------------------------------------------------------
    # Construct readable estimate message
    # ----------------------------------------------------------
    def make_estimate_message(self):
        total = self.estimate_price_inr()
        return f"💸 Estimated cost ≈ ₹ {total:,} (INR)"

    # ----------------------------------------------------------
    # Build a project summary line
    # ----------------------------------------------------------
    def project_summary(self):
        total = self.estimate_price_inr()
        domain = self.state.get("domain_name")
        domain_tag = ""
        if domain:
            mark = "✅" if self.state.get("domain_available") else "❌"
            domain_tag = f" | Domain {mark} {domain}"
        return (
            f"📋 Summary: {self.state.get('project','project')} project"
            f" ≈ ₹ {total:,} INR {domain_tag}"
        )

    # ----------------------------------------------------------
    # Save the lead to SQLite database
    # ----------------------------------------------------------
    def save_lead_to_db(self):
        try:
            session = SessionLocal()
            lead = Lead(
                name=self.state.get("name"),
                project=self.state.get("project"),
                details=self.state.get("details"),
                budget=self.state.get("budget"),
                contact=self.state.get("contact"),
                has_logo=self.state.get("has_logo"),
                has_social=self.state.get("has_social"),
                contains_payment=self.state.get("contains_payment"),
                urgent=self.state.get("urgent"),
                domain_name=self.state.get("domain_name"),
                domain_available="yes" if self.state.get("domain_available") else "no",
                estimated_cost=f"₹ {self.estimate_price_inr():,}",
            )
            session.add(lead)
            session.commit()
        except Exception as err:
            print(f"❌ Error saving lead: {err}")
        finally:
            session.close()