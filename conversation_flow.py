# conversation_flow.py
import socket
from datetime import datetime
from database import Lead, SessionLocal


class Conversation:
    def __init__(self, state=None, user_name=None):
        self.state = state or {"step": "project_type"}
        # preload name from Google Auth
        if user_name:
            self.state["name"] = user_name.split(" ")[0]

    # ----------------------------------------------------------
    # Generate reply; returns dict: {"text": str, "options": list}
    # ----------------------------------------------------------
    def reply(self, text: str):
        step = self.state.get("step", "project_type")
        text = text.strip()
        low = text.lower()

        # ---------- Step 1: Project Category ----------
        if step == "project_type":
            self.state["step"] = "subtype"
            return {
                "text": f"Hi {self.state.get('name','there')}! What kind of project do you need?",
                "options": ["Website", "App", "Automation", "Bot"]
            }

        # ---------- Step 2: Sub-Type ----------
        elif step == "subtype":
            self.state["project"] = low
            if "web" in low:
                self.state["step"] = "features"
                return {
                    "text": "Awesome! What kind of website are you looking for?",
                    "options": ["Landing Page", "Portfolio", "E‑Commerce", "Other"]
                }
            elif "app" in low:
                self.state["step"] = "features"
                return {
                    "text": "Great choice! Which features would you like in your app?",
                    "options": ["Login", "Payments", "AI", "Dashboard"]
                }
            else:
                self.state["step"] = "features"
                return {
                    "text": "Cool! Tell me which features matter most to you:",
                    "options": ["Automation", "AI", "Integrations"]
                }

        # ---------- Step 3: Features ----------
        elif step == "features":
            # store multiple selections if given
            feats = [f.strip().lower() for f in text.split(",")]
            self.state["features"] = feats
            self.state["contains_payment"] = any("payment" in f for f in feats)
            self.state["step"] = "budget"
            return {
                "text": "What’s your planned budget range (₹)?",
                "options": ["< 10 000", "10 – 30 k", "30 k +"]
            }

        # ---------- Step 4: Budget ----------
        elif step == "budget":
            self.state["budget"] = text
            self.state["step"] = "assets"
            return {
                "text": "Do you already have a logo and social media pages?",
                "options": ["Yes", "No"]
            }

        # ---------- Step 5: Assets ----------
        elif step == "assets":
            no_ans = "no" in low
            self.state["has_logo"] = not no_ans
            self.state["has_social"] = not no_ans
            self.state["step"] = "timeline"
            return {
                "text": "When do you want to launch?",
                "options": ["1 – 2 Weeks", "1 Month", "Flexible"]
            }

        # ---------- Step 6: Timeline ----------
        elif step == "timeline":
            self.state["urgent"] = "week" in low
            self.state["step"] = "domain"
            return {
                "text": "Do you already own a domain name (yes / no)? If not, type one to check (e.g., duobits.in)",
                "options": []
            }

        # ---------- Step 7: Domain ----------
        elif step == "domain":
            domain = low.replace(" ", "")
            self.state["domain_name"] = domain
            available = self.check_domain(domain)
            self.state["domain_available"] = available
            self.state["step"] = "quote"
            yes_no = "✅ available" if available else "❌ taken"
            return {
                "text": f"The domain ‘{domain}’ is {yes_no}. Would you like to see the estimated cost?",
                "options": ["Yes", "No"]
            }

        # ---------- Step 8: Show Quote ----------
        elif step == "quote":
            self.state["step"] = "done"

            # save to database as a lead
            self.save_lead_to_db()

            cost = self.estimate_price_inr()
            summary = self.project_summary(cost)
            return {
                "text": f"{summary}\n\n💸 Estimated cost ≈ ₹ {cost:,} (INR)\nOur team will reach out soon to {self.state.get('name','you')}!",
                "options": ["Start New Project"]
            }

        # ---------- Restart ----------
        elif step == "done":
            if "start" in low or "new" in low or "hello" in low:
                self.state = {"step": "project_type", "name": self.state.get("name")}
                return {
                    "text": "Let's start a new project discussion!",
                    "options": ["Website", "App", "Automation", "Bot"]
                }
            return {"text": "Type 'Start New Project' to begin again.", "options": []}

        # ---------- Fallback ----------
        return {"text": "🤖 Sorry, I didn’t get that — please select an option above or type again.", "options": []}

    # ----------------------------------------------------------
    # Domain checker (socket‑based)
    # ----------------------------------------------------------
    def check_domain(self, domain_name: str) -> bool:
        try:
            socket.gethostbyname(domain_name)
            return False  # DNS found → taken
        except socket.gaierror:
            return True   # no DNS → probably available

    # ----------------------------------------------------------
    # Price estimation (INR)
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
        base = next((price for k, price in base_table.items() if k in proj or k in sub), 8000)

        # feature adjustments
        addons = 0
        feats = self.state.get("features", [])
        for f in feats:
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

    # ----------------------------------------------------------
    # Project summary builder
    # ----------------------------------------------------------
    def project_summary(self, total):
        domain = self.state.get("domain_name")
        mark = ""
        if domain:
            mark = "✅" if self.state.get("domain_available") else "❌"
            domain = f" | Domain {mark} {domain}"
        return f"📋 {self.state.get('name','Client')}, your {self.state.get('project','project')} project summary {domain}"

    # ----------------------------------------------------------
    # Save lead to SQLite
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
                domain_name=self.state.get("domain_name"),
                domain_available="yes" if self.state.get("domain_available") else "no",
                estimated_cost=f"₹ {self.estimate_price_inr():,}",
            )
            session.add(lead)
            session.commit()
        except Exception as err:
            print(f"❌ Error saving lead: {err}")
        finally:
            session.close()