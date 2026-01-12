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
    # Generate reply; always returns dict: {"text": str, "options": list}
    # ----------------------------------------------------------
    def reply(self, text: str):
        step = self.state.get("step", "project_type")
        text = text.strip()
        low = text.lower()

        # ---------- Step 1: Project Category ----------
        if step == "project_type":
            self.state["step"] = "subtype"
            user = self.state.get("name", "there")
            return {
                "text": f"👋 Hi {user}! I'm AIBit — your DuooBits assistant. What kind of project do you need?",
                "options": ["Website", "App", "Automation", "Bot"],
            }

        # ---------- Step 2: Sub‑Type ----------
        elif step == "subtype":
            self.state["project"] = low
            self.state["subtype"] = low
            self.state["step"] = "features"

            if "web" in low:
                return {
                    "text": "Awesome! What type of website are you planning to build?",
                    "options": ["Landing Page", "Portfolio", "E‑Commerce", "Corporate"],
                }
            elif "app" in low:
                return {
                    "text": "Great choice! Which features would you like in your app?",
                    "options": ["Login", "Payments", "AI", "Dashboard"],
                }
            else:
                return {
                    "text": "Cool! Tell me which core features matter most to you:",
                    "options": ["Automation", "AI", "Integration", "Dashboard"],
                }

        # ---------- Step 3: Features (supports multi‑selection) ----------
        elif step == "features":
            # Accept multiple selections separated by comma or "and"
            feats = [f.strip().lower() for f in text.replace(" and ", ",").split(",") if f.strip()]
            self.state["features"] = feats
            self.state["contains_payment"] = any("payment" in f for f in feats)
            self.state["step"] = "budget"

            pretty = ", ".join([f.title() for f in feats]) if feats else "no specific"
            return {
                "text": f"Got it 👌 Selected features: {pretty}.\nNow, what’s your budget range (₹)?",
                "options": ["< 10 000", "10 – 30 k", "30 k +"],
            }

        # ---------- Step 4: Budget ----------
        elif step == "budget":
            self.state["budget"] = text
            self.state["step"] = "assets"
            return {
                "text": "Do you already have a logo and social media pages for your business?",
                "options": ["Yes", "No"],
            }

        # ---------- Step 5: Assets ----------
        elif step == "assets":
            no_ans = "no" in low
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
            self.state["step"] = "domain"
            return {
                "text": "Do you already own a domain name (yes / no)? If not, tell me one to check (e.g., duobits.in)",
                "options": [],
            }

        # ---------- Step 7: Domain ----------
        elif step == "domain":
            domain = low.replace(" ", "")
            self.state["domain_name"] = domain
            available = self.check_domain(domain)
            self.state["domain_available"] = available
            self.state["step"] = "quote"
            status = "✅ available" if available else "❌ already taken"
            return {
                "text": f"The domain ‘{domain}’ is {status}. Would you like to see the cost estimate?",
                "options": ["Yes", "No"],
            }

        # ---------- Step 8: Show Quote ----------
        elif step == "quote":
            self.state["step"] = "done"

            # save to database as a lead
            self.save_lead_to_db()

            cost = self.estimate_price_inr()
            summary = self.project_summary(cost)
            return {
                "text": f"{summary}\n\n💸 Estimated cost ≈ ₹ {cost:,} INR.\nOur team will reach out soon, {self.state.get('name','friend')}!",
                "options": ["Start New Project"],
            }

        # ---------- Restart / Done ----------
        elif step == "done":
            if "start" in low or "new" in low or "hello" in low:
                self.state = {"step": "project_type", "name": self.state.get("name")}
                return {
                    "text": "Let's start over and plan a new project!",
                    "options": ["Website", "App", "Automation", "Bot"],
                }
            return {"text": "Type 'Start New Project' to begin again.", "options": []}

        # ---------- Fallback ----------
        return {
            "text": "🤖 Sorry, I didn’t catch that — please choose one of the options or rephrase 🙂",
            "options": [],
        }

    # ----------------------------------------------------------
    # Domain checker (simple DNS test)
    # ----------------------------------------------------------
    def check_domain(self, domain_name: str) -> bool:
        try:
            socket.gethostbyname(domain_name)
            return False  # DNS record exists → taken
        except socket.gaierror:
            return True   # No DNS record → likely available

    # ----------------------------------------------------------
    # Estimate cost in INR
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

        # Feature‑based adjustments
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

        # Assets, urgency
        if not self.state.get("has_logo", True):
            addons += 2000
        if not self.state.get("has_social", True):
            addons += 1500
        if self.state.get("urgent"):
            base = int(base * 1.1)

        return base + addons

    # ----------------------------------------------------------
    # Project summary text
    # ----------------------------------------------------------
    def project_summary(self, total):
        domain = self.state.get("domain_name")
        mark = ""
        if domain:
            mark = "✅" if self.state.get("domain_available") else "❌"
            domain = f" | Domain {mark} {domain}"
        return (
            f"📋 Summary for {self.state.get('name','Client')}: "
            f"{self.state.get('project','project')} project"
            f" ≈ ₹ {total:,} INR {domain}"
        )

    # ----------------------------------------------------------
    # Save lead to local SQLite
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