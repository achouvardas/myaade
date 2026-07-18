import os
import uuid
import base64
from datetime import date, datetime
from decimal import Decimal
from xml.etree.ElementTree import Element, SubElement, fromstring, tostring

import requests
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "unsafe-local-development-key"),
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///myaade.sqlite3"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
db = SQLAlchemy(app)

ENVIRONMENTS = {
    "local": {"label": "Local simulation", "url": None, "safe": True},
    "demo": {"label": "Demo / AADE Test", "url": "https://mydataapidev.aade.gr", "safe": True},
    "development": {"label": "Demo / AADE Test", "url": "https://mydataapidev.aade.gr", "safe": True},
    "production": {"label": "AADE Production", "url": "https://mydatapi.aade.gr/myDATA", "safe": False},
}
VAT_CATEGORIES = {"24": "1", "13": "2", "6": "3", "17": "4", "9": "5", "4": "6", "0": "7", "3": "9"}
VAT_EXEMPTION_REASONS = {str(code): f"AADE exemption reason {code}" for code in range(1, 32)}
INVOICE_TYPES = {
    "1.1": "Τιμολόγιο Πώλησης", "1.2": "Τιμολόγιο Πώλησης / Ενδοκοινοτικές Παραδόσεις", "1.3": "Τιμολόγιο Πώλησης / Παραδόσεις Τρίτων Χωρών", "1.4": "Τιμολόγιο Πώλησης / Λογαριασμό Τρίτων", "1.5": "Τιμολόγιο Πώλησης / Εκκαθάριση Πωλήσεων Τρίτων", "1.6": "Τιμολόγιο Πώλησης / Συμπληρωματικό", "2.1": "Τιμολόγιο Παροχής", "2.2": "Τιμολόγιο Παροχής / Ενδοκοινοτική", "2.3": "Τιμολόγιο Παροχής / Τρίτη Χώρα", "2.4": "Τιμολόγιο Παροχής / Συμπληρωματικό", "3.1": "Τίτλος Κτήσης (μη υπόχρεος Εκδότης)", "3.2": "Τίτλος Κτήσης (άρνηση έκδοσης)", "5.1": "Πιστωτικό Τιμολόγιο / Συσχετιζόμενο", "5.2": "Πιστωτικό Τιμολόγιο / Μη Συσχετιζόμενο", "6.1": "Στοιχείο Αυτοπαράδοσης", "6.2": "Στοιχείο Ιδιοχρησιμοποίησης", "7.1": "Συμβόλαιο - Έσοδο", "8.1": "Ενοίκια - Έσοδο", "8.2": "Τέλος ανθεκτικότητας κλιματικής κρίσης", "8.4": "Απόδειξη Είσπραξης POS", "8.5": "Απόδειξη Επιστροφής POS", "8.6": "Δελτίο Παραγγελίας Εστίασης", "9.1": "Δελτίο Αποστολής Συσχετιζόμενο", "9.2": "Συγκεντρωτικό Δελτίο Αποστολής", "9.3": "Δελτίο Αποστολής", "10.1": "Δελτίο Ποσοτικής Παραλαβής Συσχετιζόμενο", "10.2": "Δελτίο Ποσοτικής Παραλαβής Μη Συσχετιζόμενο", "11.1": "ΑΛΠ", "11.2": "ΑΠΥ", "11.3": "Απλοποιημένο Τιμολόγιο", "11.4": "Πιστωτικό Στοιχ. Λιανικής", "11.5": "Απόδειξη Λιανικής για Λογαριασμό Τρίτων", "13.1": "Έξοδα - Αγορές Λιανικών", "13.2": "Παροχή Λιανικών", "13.3": "Κοινόχρηστα", "13.4": "Συνδρομές", "13.30": "Παραστατικά Οντότητας ως Αναγράφονται", "13.31": "Πιστωτικό Στοιχ. Λιανικής", "14.1": "Τιμολόγιο / Ενδοκοινοτικές Αποκτήσεις", "14.2": "Τιμολόγιο / Αποκτήσεις Τρίτων Χωρών", "14.3": "Τιμολόγιο / Ενδοκοινοτική Λήψη Υπηρεσιών", "14.4": "Τιμολόγιο / Λήψη Υπηρεσιών Τρίτων Χωρών", "14.5": "ΕΦΚΑ και λοιποί Ασφαλιστικοί Οργανισμοί", "14.30": "Παραστατικά Οντότητας ως Αναγράφονται", "14.31": "Πιστωτικό ημεδαπής / αλλοδαπής", "15.1": "Συμβόλαιο - Έξοδο", "16.1": "Ενοίκιο Έξοδο", "17.1": "Μισθοδοσία", "17.2": "Αποσβέσεις", "17.3": "Λοιπές Εγγραφές Τακτοποίησης Εσόδων - Λογιστική Βάση", "17.4": "Λοιπές Εγγραφές Τακτοποίησης Εσόδων - Φορολογική Βάση", "17.5": "Λοιπές Εγγραφές Τακτοποίησης Εξόδων - Λογιστική Βάση", "17.6": "Λοιπές Εγγραφές Τακτοποίησης Εξόδων - Φορολογική Βάση",
}
COPY = {
    "en": {"dashboard":"Dashboard", "new_invoice":"New invoice", "invoices":"Invoices", "workspace":"Personal finance workspace", "ready":"Ready to review", "send":"Send to myDATA", "settings":"Settings", "recent":"Recent invoices"},
    "el": {"dashboard":"Πίνακας ελέγχου", "new_invoice":"Νέο παραστατικό", "invoices":"Παραστατικά", "workspace":"Προσωπικός χώρος οικονομικών", "ready":"Έτοιμο για έλεγχο", "send":"Αποστολή στο myDATA", "settings":"Ρυθμίσεις", "recent":"Πρόσφατα παραστατικά"},
}

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(40), unique=True, nullable=False)
    invoice_type = db.Column(db.String(8), nullable=False, default="1.1")
    customer = db.Column(db.String(160), nullable=False)
    vat_number = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    net = db.Column(db.Numeric(12, 2), nullable=False)
    vat_rate = db.Column(db.Numeric(5, 2), nullable=False, default=24)
    issue_date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(30), nullable=False, default="draft")
    mydata_mark = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def vat_amount(self): return self.net * self.vat_rate / 100
    @property
    def total(self): return self.net + self.vat_amount

class InvoiceLine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)
    net = db.Column(db.Numeric(12, 2), nullable=False)
    vat_rate = db.Column(db.Numeric(5, 2), nullable=False, default=24)
    vat_exemption_reason = db.Column(db.String(3))

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    vat_number = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.String(300))
    vies_checked_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class AppSetting(db.Model):
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, nullable=False)
    encrypted = db.Column(db.Boolean, nullable=False, default=False)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(80), nullable=False)
    detail = db.Column(db.Text, nullable=False, default="")
    payload = db.Column(db.Text)
    actor = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

def locale(): return session.get("locale", "en")
@app.context_processor
def inject_ui(): return {"t": COPY[locale()], "locale": locale(), "mode": setting("mydata_mode", current_mode()) if User.query.first() else current_mode(), "current_user": current_user()}
def current_mode(): return os.getenv("MYDATA_MODE", "demo").lower()
def cipher():
    key_path = os.path.join(app.instance_path, "myaade-master.key")
    os.makedirs(app.instance_path, exist_ok=True)
    if not os.path.exists(key_path):
        with open(key_path, "wb") as handle: handle.write(Fernet.generate_key())
        os.chmod(key_path, 0o600)
    with open(key_path, "rb") as handle: return Fernet(handle.read())
def setting(key, default=""):
    item = db.session.get(AppSetting, key)
    if not item: return default
    return cipher().decrypt(item.value.encode()).decode() if item.encrypted else item.value
def set_setting(key, value, encrypted=False):
    item = db.session.get(AppSetting, key) or AppSetting(key=key, value="")
    item.encrypted, item.value = encrypted, (cipher().encrypt(value.encode()).decode() if encrypted and value else value)
    db.session.add(item)
def audit(action, detail="", payload=None):
    db.session.add(ActivityLog(action=action, detail=detail, payload=payload, actor=session.get("user_email"))); db.session.commit()
def current_user(): return db.session.get(User, session.get("user_id")) if session.get("user_id") else None
def require_admin():
    if not current_user() or current_user().role != "admin": abort(403)
def turnstile_ok(token):
    secret = setting("turnstile_secret")
    if not secret: return True
    if not token: return False
    try:
        result = requests.post("https://challenges.cloudflare.com/turnstile/v0/siteverify", data={"secret": secret, "response": token, "remoteip": request.remote_addr}, timeout=8).json()
        return result.get("success", False)
    except requests.RequestException: return False

@app.before_request
def protect_app():
    public = {"setup", "login", "health", "static"}
    if not User.query.first() and request.endpoint not in public: return redirect(url_for("setup"))
    if User.query.first() and not current_user() and request.endpoint not in public: return redirect(url_for("login"))

def invoice_xml(invoice):
    root = Element("InvoicesDoc", {"xmlns": "http://www.aade.gr/myDATA/invoice/v1.0"})
    inv = SubElement(root, "invoice")
    issuer, counterpart = SubElement(inv, "issuer"), SubElement(inv, "counterpart")
    SubElement(issuer, "vatNumber").text, SubElement(issuer, "country").text, SubElement(issuer, "branch").text = setting("business_vat", os.getenv("MYDATA_VAT_NUMBER", "")), "GR", "0"
    SubElement(counterpart, "vatNumber").text, SubElement(counterpart, "country").text = invoice.vat_number, "GR"
    header = SubElement(inv, "invoiceHeader")
    SubElement(header, "series").text, SubElement(header, "aa").text = setting("invoice_series", "A"), invoice.number
    SubElement(header, "issueDate").text, SubElement(header, "invoiceType").text = invoice.issue_date.isoformat(), invoice.invoice_type
    lines = InvoiceLine.query.filter_by(invoice_id=invoice.id).order_by(InvoiceLine.id).all()
    if not lines: lines = [type("LegacyLine", (), {"net": invoice.net, "vat_rate": invoice.vat_rate, "vat_exemption_reason": None})()]
    total_net, total_vat = Decimal("0"), Decimal("0")
    for number, line in enumerate(lines, 1):
        details = SubElement(inv, "invoiceDetails"); vat_rate = Decimal(line.vat_rate); vat_amount = Decimal(line.net) * vat_rate / 100
        SubElement(details, "lineNumber").text, SubElement(details, "netValue").text = str(number), f"{line.net:.2f}"
        vat_key = str(int(vat_rate)) if vat_rate == vat_rate.to_integral() else str(vat_rate)
        SubElement(details, "vatCategory").text, SubElement(details, "vatAmount").text = VAT_CATEGORIES.get(vat_key, "7"), f"{vat_amount:.2f}"
        if vat_rate == 0: SubElement(details, "vatExemptionCategory").text = line.vat_exemption_reason
        total_net += Decimal(line.net); total_vat += vat_amount
    summary = SubElement(inv, "invoiceSummary")
    SubElement(summary, "totalNetValue").text, SubElement(summary, "totalVatAmount").text = f"{total_net:.2f}", f"{total_vat:.2f}"
    for field in ("totalWithheldAmount", "totalFeesAmount", "totalStampDutyAmount", "totalOtherTaxesAmount", "totalDeductionsAmount"): SubElement(summary, field).text = "0.00"
    SubElement(summary, "totalGrossValue").text = f"{total_net + total_vat:.2f}"
    return tostring(root, encoding="utf-8", xml_declaration=True)

def transmit(invoice):
    mode = setting("mydata_mode", current_mode())
    xml = invoice_xml(invoice)
    if mode == "local":
        mark = "DEMO-" + uuid.uuid4().hex[:10].upper(); audit("xml_sent", f"Demo SendInvoices for {invoice.number}", xml.decode()); audit("xml_received", f"Demo response for {invoice.number}", f"<response><mark>{mark}</mark></response>"); return mark
    config = ENVIRONMENTS.get(mode)
    user, key = setting("mydata_user_id"), setting("mydata_subscription_key")
    if not config or not user or not key: raise ValueError("AADE credentials are missing. Add them only to your local environment.")
    audit("xml_sent", f"SendInvoices for {invoice.number}", xml.decode())
    response = requests.post(config["url"] + "/SendInvoices", data=xml, headers={"aade-user-id": setting("mydata_user_id"), "ocp-apim-subscription-key": setting("mydata_subscription_key"), "Content-Type": "application/xml"}, timeout=20)
    response.raise_for_status(); audit("xml_received", f"AADE response for {invoice.number}", response.text)
    response_fields = {node.tag.rsplit("}", 1)[-1]: (node.text or "").strip() for node in fromstring(response.content).iter()}
    if response_fields.get("statusCode") != "Success" or not response_fields.get("invoiceMark"):
        raise ValueError(response_fields.get("message") or response_fields.get("errors") or "AADE did not accept the invoice; inspect received XML in Developer Logs.")
    return response_fields["invoiceMark"]

@app.get("/")
def dashboard():
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    total = sum((i.total for i in invoices if i.status == "transmitted"), Decimal("0"))
    return render_template("dashboard.html", invoices=invoices[:5], total=total, drafts=sum(i.status == "draft" for i in invoices))

@app.route("/setup", methods=["GET", "POST"])
def setup():
    if User.query.first(): return redirect(url_for("login"))
    if request.method == "POST":
        email, password = request.form["email"].strip().lower(), request.form["password"]
        if len(password) < 12: flash("Use an administrator password of at least 12 characters.", "error"); return redirect(url_for("setup"))
        db.session.add(User(email=email, password_hash=generate_password_hash(password), role="admin"))
        for key, secret in [("mydata_mode", False), ("mydata_user_id", True), ("mydata_subscription_key", True), ("turnstile_sitekey", False), ("turnstile_secret", True), ("invoice_series", False), ("invoice_next_number", False)]: set_setting(key, request.form.get(key, "demo" if key == "mydata_mode" else ""), secret)
        db.session.commit(); session["user_id"], session["user_email"] = User.query.filter_by(email=email).one().id, email; audit("setup_complete", "First administrator and encrypted settings created"); return redirect(url_for("dashboard"))
    return render_template("setup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if not User.query.first(): return redirect(url_for("setup"))
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"].strip().lower()).first()
        if not turnstile_ok(request.form.get("cf-turnstile-response")) or not user or not check_password_hash(user.password_hash, request.form["password"]): flash("Invalid credentials or Turnstile verification.", "error"); audit("login_failed", request.form["email"]); return redirect(url_for("login"))
        session.clear(); session["user_id"], session["user_email"] = user.id, user.email; audit("login", "Successful login"); return redirect(url_for("dashboard"))
    return render_template("login.html", turnstile_sitekey=setting("turnstile_sitekey"))
@app.post("/logout")
def logout(): audit("logout"); session.clear(); return redirect(url_for("login"))

@app.route("/settings", methods=["GET", "POST"])
def settings():
    require_admin()
    if request.method == "POST":
        for key, secret in [("mydata_mode", False), ("mydata_user_id", True), ("mydata_subscription_key", True), ("turnstile_sitekey", False), ("turnstile_secret", True), ("invoice_series", False), ("invoice_next_number", False)]:
            value = request.form.get(key, "")
            if value or not secret: set_setting(key, value, secret)
        db.session.commit(); audit("settings_updated", "Administrator updated integration and numbering settings"); flash("Settings saved. Secrets are encrypted at rest.", "success"); return redirect(url_for("settings"))
    values = {key: setting(key) for key in ["mydata_mode", "turnstile_sitekey", "invoice_series", "invoice_next_number"]}
    return render_template("settings.html", values=values, configured={"mydata_user_id": bool(setting("mydata_user_id")), "mydata_subscription_key": bool(setting("mydata_subscription_key")), "turnstile_secret": bool(setting("turnstile_secret"))})
@app.route("/business-settings", methods=["GET", "POST"])
def business_settings():
    require_admin(); fields = ("business_legal_name", "business_activity", "business_vat", "business_doy", "business_address", "business_email", "business_phone", "business_gemi", "business_website")
    if request.method == "POST":
        for field in fields: set_setting(field, request.form.get(field, ""))
        db.session.commit(); audit("business_profile_updated"); flash("Business profile saved.", "success"); return redirect(url_for("business_settings"))
    defaults = {"business_legal_name":"ΚΙΝΕΖΟΥ ΜΑΡΙΝΑ ΤΟΥ ΑΘΑΝΑΣΙΟΥ", "business_activity":"ΕΚΔΟΣΗ ΕΝΤΥΠΩΝ ΕΦΗΜΕΡΙΔΩΝ", "business_vat":"113959169", "business_doy":"ΚΟΜΟΤΗΝΗΣ", "business_address":"ΚΑΣΤΕΛΟΡΙΖΟΥ 2, ΚΟΜΟΤΗΝΗ, Ν. ΡΟΔΟΠΗΣ ΤΚ. 69100", "business_email":"marinakinneathrakis@gmail.com", "business_phone":"6982970176", "business_gemi":"053724811000", "business_website":"www.thrakionline.gr"}
    return render_template("business_settings.html", values={field: setting(field, defaults[field]) for field in fields})
@app.route("/users", methods=["GET", "POST"])
def users():
    require_admin()
    if request.method == "POST":
        email, password = request.form["email"].strip().lower(), request.form["password"]
        if User.query.filter_by(email=email).first() or len(password) < 12: flash("Email already exists or password is under 12 characters.", "error")
        else: db.session.add(User(email=email, password_hash=generate_password_hash(password), role=request.form.get("role", "user"))); db.session.commit(); audit("user_created", email); flash("User created.", "success")
        return redirect(url_for("users"))
    return render_template("users.html", users=User.query.order_by(User.created_at).all())
@app.get("/logs")
def logs(): require_admin(); return render_template("logs.html", logs=ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(100).all())
@app.get("/invoices/<int:invoice_id>/pdf")
def invoice_pdf(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id); path = os.path.join(app.instance_path, f"invoice-{invoice.id}.pdf"); lines = InvoiceLine.query.filter_by(invoice_id=invoice.id).all(); font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; pdfmetrics.registerFont(TTFont("SiraSans", font_path))
    canvas = Canvas(path, pagesize=A4); canvas.setFillColor(HexColor("#ffffff")); canvas.rect(0, 0, 595, 842, fill=1, stroke=0); canvas.setFillColor(HexColor("#1e293b")); canvas.setFont("SiraSans", 24); canvas.drawString(42, 795, "myAade"); canvas.setFont("SiraSans", 12); canvas.drawString(42, 765, f"{INVOICE_TYPES.get(invoice.invoice_type, invoice.invoice_type)} · {invoice.number} · {invoice.issue_date.isoformat()}"); canvas.drawString(42, 730, f"ΠΕΛΑΤΗΣ: {invoice.customer}"); canvas.drawString(42, 710, f"ΑΦΜ: {invoice.vat_number} · Τύπος myDATA: {invoice.invoice_type}")
    y = 660; canvas.setFillColor(HexColor("#e2e8f0")); canvas.rect(42, y, 510, 25, fill=1, stroke=0); canvas.setFillColor(HexColor("#1e293b")); canvas.setFont("SiraSans", 10); canvas.drawString(50, y+8, "Α/Α"); canvas.drawString(95, y+8, "ΠΕΡΙΓΡΑΦΗ"); canvas.drawRightString(535, y+8, "ΣΥΝΟΛΟ"); canvas.setFont("SiraSans", 10)
    for index, line in enumerate(lines or [type("L", (), {"description":invoice.description,"net":invoice.net})()], 1): y -= 30; canvas.setFillColor(HexColor("#1e293b")); canvas.drawString(50, y+8, str(index)); canvas.drawString(95, y+8, str(line.description)[:65]); canvas.drawRightString(535, y+8, f"{line.net:.2f} €")
    canvas.setFont("SiraSans", 11); canvas.drawRightString(535, 150, f"ΚΑΘΑΡΗ ΑΞΙΑ: {invoice.net:.2f} €"); canvas.drawRightString(535, 125, f"Φ.Π.Α.: {invoice.vat_amount:.2f} €"); canvas.setFont("SiraSans", 15); canvas.drawRightString(535, 90, f"ΣΥΝΟΛΙΚΟ ΠΟΣΟ: {invoice.total:.2f} €"); canvas.setFont("SiraSans", 9); canvas.drawString(42, 150, "Το παρόν διαβιβάστηκε επιτυχώς στο myDATA της ΑΑΔΕ." if invoice.mydata_mark else "Πρόχειρο — δεν έχει ακόμη διαβιβαστεί στο myDATA."); canvas.drawString(42, 130, f"MARK: {invoice.mydata_mark or '-'}"); canvas.save(); audit("pdf_generated", f"Invoice {invoice.number}"); return send_file(path, as_attachment=False, download_name=f"invoice-{invoice.number}.pdf", mimetype="application/pdf")

@app.route("/invoices/new", methods=["GET", "POST"])
def new_invoice():
    if request.method == "POST":
        invoice_type = request.form["invoice_type"]
        if invoice_type not in INVOICE_TYPES: flash("Invalid AADE invoice type.", "error"); return redirect(url_for("new_invoice"))
        descriptions, nets, rates, reasons = request.form.getlist("line_description"), request.form.getlist("line_net"), request.form.getlist("line_vat_rate"), request.form.getlist("line_vat_exemption_reason")
        try:
            parsed = [(description, Decimal(net), Decimal(rate), reason if Decimal(rate) == 0 else None) for description, net, rate, reason in zip(descriptions, nets, rates, reasons)]
            if not parsed or any(rate == 0 and reason not in VAT_EXEMPTION_REASONS for _, _, rate, reason in parsed): raise ValueError
        except (ValueError, ArithmeticError): flash("Add at least one valid line and an AADE VAT exemption reason for every 0% VAT line.", "error"); return redirect(url_for("new_invoice"))
        total_net, total_vat = sum((net for _, net, _, _ in parsed), Decimal("0")), sum((net * rate / 100 for _, net, rate, _ in parsed), Decimal("0"))
        retail = invoice_type in {"11.1", "11.2"}
        invoice = Invoice(number=request.form["number"], invoice_type=invoice_type, customer="ΠΕΛΑΤΗΣ ΛΙΑΝΙΚΗΣ" if retail else request.form["customer"], vat_number="000000000" if retail else request.form["vat_number"], description=parsed[0][0], net=total_net, vat_rate=(total_vat / total_net * 100 if total_net else Decimal("0")), issue_date=date.fromisoformat(request.form["issue_date"]))
        db.session.add(invoice)
        db.session.flush()
        for description, net, rate, reason in parsed: db.session.add(InvoiceLine(invoice_id=invoice.id, description=description, net=net, vat_rate=rate, vat_exemption_reason=reason))
        if request.form["number"].isdigit(): set_setting("invoice_next_number", str(int(request.form["number"]) + 1))
        db.session.commit(); audit("invoice_draft", f"Created {invoice.number}"); flash("Invoice saved as draft.", "success"); return redirect(url_for("invoice_detail", invoice_id=invoice.id))
    priority = ["1.1", "2.1", "11.1", "11.2"]
    ordered_types = dict(sorted(INVOICE_TYPES.items(), key=lambda item: (priority.index(item[0]) if item[0] in priority else 99, item[0])))
    return render_template("invoice_form.html", today=date.today().isoformat(), clients=Client.query.order_by(Client.name).all(), invoice_types=ordered_types, next_number=setting("invoice_next_number", "1"), series=setting("invoice_series", "A"), exemption_reasons=VAT_EXEMPTION_REASONS)

@app.get("/invoices/<int:invoice_id>")
def invoice_detail(invoice_id): return render_template("invoice_detail.html", invoice=db.get_or_404(Invoice, invoice_id))
@app.post("/invoices/<int:invoice_id>/send")
def send_invoice(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    try:
        invoice.mydata_mark, invoice.status = transmit(invoice), "transmitted"; db.session.commit(); flash(f"Submitted successfully — MARK {invoice.mydata_mark}", "success")
    except (ValueError, requests.RequestException) as error: flash(str(error), "error")
    return redirect(url_for("invoice_detail", invoice_id=invoice.id))
@app.get("/invoices")
def invoices(): return render_template("invoices.html", invoices=Invoice.query.order_by(Invoice.created_at.desc()).all())
@app.post("/invoices/<int:invoice_id>/delete")
def delete_invoice(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    if setting("mydata_mode", "demo") not in {"demo", "local"}: flash("Deletion is disabled outside Demo mode.", "error")
    elif invoice.status == "transmitted": flash("A transmitted invoice cannot be deleted; cancel it through AADE.", "error")
    else: InvoiceLine.query.filter_by(invoice_id=invoice.id).delete(); db.session.delete(invoice); db.session.commit(); audit("invoice_deleted", invoice.number); flash("Draft invoice deleted.", "success")
    return redirect(url_for("invoices"))
def check_vies(raw_vat):
    vat = "".join(char for char in raw_vat.upper().replace("GR", "").replace("EL", "") if char.isalnum())
    if not vat.isdigit() or len(vat) != 9: raise ValueError("Enter a 9-digit Greek VAT number.")
    payload = f'<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:ec.europa.eu:taxud:vies:services:checkVat:types"><soapenv:Body><urn:checkVat><urn:countryCode>EL</urn:countryCode><urn:vatNumber>{vat}</urn:vatNumber></urn:checkVat></soapenv:Body></soapenv:Envelope>'
    response = requests.post("https://ec.europa.eu/taxation_customs/vies/services/checkVatService", data=payload.encode(), headers={"Content-Type": "text/xml; charset=utf-8"}, timeout=12); response.raise_for_status()
    fields = {node.tag.rsplit("}", 1)[-1]: (node.text or "").strip() for node in fromstring(response.content).iter()}
    if fields.get("valid", "false").lower() != "true": raise ValueError("VIES returned no valid registration. The VAT format may be valid; check VIES/AADE status and retry later.")
    return vat, fields.get("name", "Verified Greek business").split("||", 1)[0].strip(), fields.get("address", "")
@app.route("/clients", methods=["GET", "POST"])
def clients():
    if request.method == "POST":
        try:
            vat, name, address = check_vies(request.form["vat_number"]); client = Client.query.filter_by(vat_number=vat).first()
            if client: client.name, client.address, client.vies_checked_at = name, address, datetime.utcnow()
            else: db.session.add(Client(name=name, vat_number=vat, address=address))
            db.session.commit(); flash(f"{name} verified with VIES and saved.", "success")
        except (ValueError, requests.RequestException) as error: audit("vies_failed", str(error)); flash(f"VIES validation unavailable: {error}", "error")
        return redirect(url_for("clients"))
    return render_template("clients.html", clients=Client.query.order_by(Client.name).all())
@app.post("/clients/<int:client_id>/delete")
def delete_client(client_id):
    if setting("mydata_mode", "demo") not in {"demo", "local"}: flash("Deletion is disabled outside Demo mode.", "error"); return redirect(url_for("clients"))
    client = db.get_or_404(Client, client_id); db.session.delete(client); db.session.commit(); audit("client_deleted", client.vat_number); flash("Client deleted.", "success"); return redirect(url_for("clients"))
@app.post("/locale/<code>")
def set_locale(code): session["locale"] = code if code in COPY else "en"; return redirect(request.referrer or url_for("dashboard"))
@app.get("/health")
def health(): return jsonify(status="ok", mode=current_mode(), database="sqlite")

with app.app_context(): db.create_all()
if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", host="127.0.0.1", port=int(os.getenv("PORT", "5000")))
