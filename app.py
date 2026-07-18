import os
import base64
from datetime import date, datetime, timedelta
from decimal import Decimal
from xml.etree.ElementTree import Element, SubElement, fromstring, register_namespace, tostring

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
from reportlab.graphics.barcode import qr
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func, inspect, text

load_dotenv()
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "unsafe-key"),
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///myaade.sqlite3"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
db = SQLAlchemy(app)

ENVIRONMENTS = {
    "test": {"label": "AADE Test", "url": "https://mydataapidev.aade.gr"},
    "production": {"label": "AADE Production", "url": "https://mydatapi.aade.gr/myDATA"},
}
VAT_CATEGORIES = {"24": "1", "13": "2", "6": "3", "17": "4", "9": "5", "4": "6", "0": "7", "3": "9"}
VAT_EXEMPTION_REASONS = {str(code): f"AADE exemption reason {code}" for code in range(1, 32)}
INCOME_CATEGORIES = {
    "category1_1": "Έσοδα από πώληση εμπορευμάτων",
    "category1_2": "Έσοδα από πώληση προϊόντων",
    "category1_3": "Έσοδα από παροχή υπηρεσιών",
    "category1_4": "Έσοδα από πώληση παγίων",
    "category1_5": "Λοιπά έσοδα / κέρδη",
    "category1_6": "Αυτοπαραδόσεις / ιδιοχρησιμοποιήσεις",
    "category1_7": "Έσοδα για λογαριασμό τρίτων",
    "category1_8": "Έσοδα προηγούμενων χρήσεων",
    "category1_9": "Έσοδα επόμενων χρήσεων",
    "category1_10": "Λοιπές εγγραφές τακτοποίησης εσόδων",
    "category1_95": "Λοιπά πληροφοριακά στοιχεία εσόδων",
    "category3": "Διακίνηση",
}
INCOME_TYPES = {
    "E3_561_001": "Πωλήσεις αγαθών και υπηρεσιών χονδρικές",
    "E3_561_002": "Χονδρικές βάσει άρθρου 39α παρ. 5 ΦΠΑ",
    "E3_561_003": "Πωλήσεις αγαθών και υπηρεσιών λιανικές",
    "E3_561_004": "Λιανικές βάσει άρθρου 39α παρ. 5 ΦΠΑ",
    "E3_561_005": "Πωλήσεις εξωτερικού ενδοκοινοτικές",
    "E3_561_006": "Πωλήσεις εξωτερικού τρίτες χώρες",
    "E3_561_007": "Πωλήσεις αγαθών και υπηρεσιών λοιπά",
    "E3_562": "Λοιπά συνήθη έσοδα",
    "E3_880_001": "Πωλήσεις παγίων χονδρικές",
    "E3_880_002": "Πωλήσεις παγίων λιανικές",
    "E3_880_003": "Πωλήσεις παγίων εξωτερικού ενδοκοινοτικές",
    "E3_880_004": "Πωλήσεις παγίων εξωτερικού τρίτες χώρες",
}
INCOME_CLASSIFICATION_NS = "https://www.aade.gr/myDATA/incomeClassificaton/v1.0"
register_namespace("income", INCOME_CLASSIFICATION_NS)
PAYMENT_METHODS = {"1": "Επαγγελματικός λογαριασμός ημεδαπής", "2": "Επαγγελματικός λογαριασμός αλλοδαπής", "3": "Μετρητά", "4": "Επιταγή", "5": "Επί πιστώσει", "6": "Web Banking", "7": "POS / e-POS", "8": "Άμεσες Πληρωμές IRIS"}
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
    invoice_uid = db.Column(db.String(80))
    qr_url = db.Column(db.Text)
    payment_method = db.Column(db.String(2), nullable=False, default="3")
    customer_address = db.Column(db.String(300))
    customer_profession = db.Column(db.String(300))
    notes = db.Column(db.Text)
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
    quantity = db.Column(db.Numeric(12, 3), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    vat_rate = db.Column(db.Numeric(5, 2), nullable=False, default=24)
    vat_exemption_reason = db.Column(db.String(3))
    income_category = db.Column(db.String(30))
    income_type = db.Column(db.String(30))

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    vat_number = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.String(300))
    profession = db.Column(db.String(300))
    gemi_number = db.Column(db.String(30))
    gemi_checked_at = db.Column(db.DateTime)
    gemi_retry_after = db.Column(db.DateTime)
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
def current_mode(): return os.getenv("MYDATA_MODE", "test").lower()
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
    SubElement(counterpart, "vatNumber").text, SubElement(counterpart, "country").text, SubElement(counterpart, "branch").text = invoice.vat_number, "GR", "0"
    header = SubElement(inv, "invoiceHeader")
    SubElement(header, "series").text, SubElement(header, "aa").text = setting("invoice_series", "A"), invoice.number
    SubElement(header, "issueDate").text, SubElement(header, "invoiceType").text = invoice.issue_date.isoformat(), invoice.invoice_type
    SubElement(header, "currency").text = "EUR"
    payment = SubElement(SubElement(inv, "paymentMethods"), "paymentMethodDetails")
    SubElement(payment, "type").text, SubElement(payment, "amount").text = invoice.payment_method or "3", f"{invoice.total:.2f}"
    lines = InvoiceLine.query.filter_by(invoice_id=invoice.id).order_by(InvoiceLine.id).all()
    if not lines: lines = [type("LegacyLine", (), {"net": invoice.net, "vat_rate": invoice.vat_rate, "vat_exemption_reason": None, "income_category": None, "income_type": None})()]
    total_net, total_vat = Decimal("0"), Decimal("0")
    for number, line in enumerate(lines, 1):
        details = SubElement(inv, "invoiceDetails"); vat_rate = Decimal(line.vat_rate); vat_amount = Decimal(line.net) * vat_rate / 100
        SubElement(details, "lineNumber").text, SubElement(details, "netValue").text = str(number), f"{line.net:.2f}"
        vat_key = str(int(vat_rate)) if vat_rate == vat_rate.to_integral() else str(vat_rate)
        SubElement(details, "vatCategory").text, SubElement(details, "vatAmount").text = VAT_CATEGORIES.get(vat_key, "7"), f"{vat_amount:.2f}"
        if vat_rate == 0: SubElement(details, "vatExemptionCategory").text = line.vat_exemption_reason
        if line.income_category: add_income_classification(details, line.income_type, line.income_category, line.net)
        total_net += Decimal(line.net); total_vat += vat_amount
    summary = SubElement(inv, "invoiceSummary")
    SubElement(summary, "totalNetValue").text, SubElement(summary, "totalVatAmount").text = f"{total_net:.2f}", f"{total_vat:.2f}"
    for field in ("totalWithheldAmount", "totalFeesAmount", "totalStampDutyAmount", "totalOtherTaxesAmount", "totalDeductionsAmount"): SubElement(summary, field).text = "0.00"
    SubElement(summary, "totalGrossValue").text = f"{total_net + total_vat:.2f}"
    classifications = {}
    for line in lines:
        if line.income_category:
            key = (line.income_type or "", line.income_category)
            classifications[key] = classifications.get(key, Decimal("0")) + Decimal(line.net)
    for (income_type, income_category), amount in classifications.items(): add_income_classification(summary, income_type, income_category, amount)
    return tostring(root, encoding="utf-8", xml_declaration=True)

def add_income_classification(parent, income_type, income_category, amount):
    classification = SubElement(parent, "incomeClassification")
    if income_type: SubElement(classification, f"{{{INCOME_CLASSIFICATION_NS}}}classificationType").text = income_type
    SubElement(classification, f"{{{INCOME_CLASSIFICATION_NS}}}classificationCategory").text = income_category
    SubElement(classification, f"{{{INCOME_CLASSIFICATION_NS}}}amount").text = f"{Decimal(amount):.2f}"

def transmit(invoice):
    mode = setting("mydata_mode", current_mode())
    if not setting("business_vat", os.getenv("MYDATA_VAT_NUMBER", "")).strip(): raise ValueError("Issuer VAT/ΑΦΜ is required. Save it in Business profile before submitting.")
    if invoice.payment_method not in PAYMENT_METHODS: raise ValueError("Choose a valid AADE payment method before submitting.")
    lines = InvoiceLine.query.filter_by(invoice_id=invoice.id).all()
    if not lines or any(not line.income_category for line in lines): raise ValueError("Every invoice line requires an income classification before submitting.")
    xml = invoice_xml(invoice)
    config = ENVIRONMENTS.get(mode)
    user, key = setting("mydata_user_id"), setting("mydata_subscription_key")
    if not config: raise ValueError("Choose AADE Test or Production in Settings before submitting.")
    if not user or not key: raise ValueError("AADE credentials are missing. Configure them in Settings before submitting.")
    audit("xml_sent", f"SendInvoices for {invoice.number}", xml.decode())
    response = requests.post(config["url"] + "/SendInvoices", data=xml, headers={"aade-user-id": setting("mydata_user_id"), "ocp-apim-subscription-key": setting("mydata_subscription_key"), "Content-Type": "application/xml"}, timeout=20)
    response.raise_for_status(); audit("xml_received", f"AADE response for {invoice.number}", response.text)
    response_fields = {node.tag.rsplit("}", 1)[-1]: (node.text or "").strip() for node in fromstring(response.content).iter()}
    if response_fields.get("statusCode") != "Success" or not response_fields.get("invoiceMark"):
        raise ValueError(response_fields.get("message") or response_fields.get("errors") or "AADE did not accept the invoice; inspect received XML in Developer Logs.")
    return {"mark": response_fields["invoiceMark"], "uid": response_fields.get("invoiceUid", ""), "qr_url": response_fields.get("qrUrl", "")}

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
        for key, secret in [("mydata_mode", False), ("mydata_user_id", True), ("mydata_subscription_key", True), ("turnstile_sitekey", False), ("turnstile_secret", True), ("invoice_series", False), ("invoice_next_number", False)]: set_setting(key, request.form.get(key, "test" if key == "mydata_mode" else ""), secret)
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
        for key, secret in [("mydata_mode", False), ("mydata_user_id", True), ("mydata_subscription_key", True), ("turnstile_sitekey", False), ("turnstile_secret", True), ("invoice_series", False), ("invoice_next_number", False), ("business_vat", False)]:
            value = request.form.get(key, "")
            if value or not secret: set_setting(key, value, secret)
        db.session.commit(); audit("settings_updated", "Administrator updated integration and numbering settings"); flash("Settings saved. Secrets are encrypted at rest.", "success"); return redirect(url_for("settings"))
    values = {key: setting(key) for key in ["mydata_mode", "turnstile_sitekey", "invoice_series", "invoice_next_number", "business_vat"]}
    return render_template("settings.html", values=values, configured={"mydata_user_id": bool(setting("mydata_user_id")), "mydata_subscription_key": bool(setting("mydata_subscription_key")), "turnstile_secret": bool(setting("turnstile_secret"))})
@app.route("/business-settings", methods=["GET", "POST"])
def business_settings():
    require_admin(); fields = ("business_legal_name", "business_activity", "business_vat", "business_doy", "business_address", "business_email", "business_phone", "business_gemi", "business_website")
    if request.method == "POST":
        for field in fields: set_setting(field, request.form.get(field, ""))
        logo = request.files.get("business_logo")
        if logo and logo.filename:
            extension = os.path.splitext(secure_filename(logo.filename))[1].lower()
            if extension not in {".png", ".jpg", ".jpeg"}: flash("Logo must be a PNG or JPG image.", "error"); return redirect(url_for("business_settings"))
            logo_path = os.path.join(app.instance_path, f"business-logo{extension}"); logo.save(logo_path); set_setting("business_logo", logo_path)
        db.session.commit(); audit("business_profile_updated"); flash("Business profile saved.", "success"); return redirect(url_for("business_settings"))
    return render_template("business_settings.html", values={field: setting(field, "") for field in fields}, logo_configured=bool(setting("business_logo", "")))
@app.get("/business-logo")
def business_logo():
    if not current_user(): abort(403)
    path = setting("business_logo", "")
    if not path or not os.path.isfile(path): abort(404)
    return send_file(path)
@app.route("/users", methods=["GET", "POST"])
def users():
    require_admin()
    if request.method == "POST":
        email, password = request.form["email"].strip().lower(), request.form["password"]
        if User.query.filter_by(email=email).first() or len(password) < 12: flash("Email already exists or password is under 12 characters.", "error")
        else: db.session.add(User(email=email, password_hash=generate_password_hash(password), role=request.form.get("role", "user"))); db.session.commit(); audit("user_created", email); flash("User created.", "success")
        return redirect(url_for("users"))
    return render_template("users.html", users=User.query.order_by(User.created_at).all())
@app.post("/users/<int:user_id>/delete")
def delete_user(user_id):
    require_admin(); user = db.get_or_404(User, user_id)
    if user.id == current_user().id: flash("You cannot delete your own active account.", "error")
    elif user.role == "admin" and User.query.filter_by(role="admin").count() <= 1: flash("Keep at least one administrator account.", "error")
    else: db.session.delete(user); db.session.commit(); audit("user_deleted", user.email); flash("User deleted.", "success")
    return redirect(url_for("users"))
@app.get("/logs")
def logs(): require_admin(); return render_template("logs.html", logs=ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(100).all())
@app.get("/logs/<int:log_id>/xml")
def view_xml_log(log_id):
    require_admin(); log = db.get_or_404(ActivityLog, log_id)
    if log.action not in {"xml_sent", "xml_received"}: abort(404)
    return app.response_class(log.payload or "", mimetype="application/xml")
@app.get("/invoices/<int:invoice_id>/pdf")
def invoice_pdf(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id); path = os.path.join(app.instance_path, f"invoice-{invoice.id}.pdf"); lines = InvoiceLine.query.filter_by(invoice_id=invoice.id).all(); pdf_lines = lines or [type("L", (), {"description": invoice.description, "net": invoice.net, "quantity": Decimal("1"), "unit_price": invoice.net, "vat_rate": invoice.vat_rate})()]; font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; pdfmetrics.registerFont(TTFont("SiraSans", font_path))
    canvas = Canvas(path, pagesize=A4); navy, slate, pale, cyan = HexColor("#0f172a"), HexColor("#334155"), HexColor("#f1f5f9"), HexColor("#0891b2"); canvas.setFillColor(HexColor("#ffffff")); canvas.rect(0, 0, 595, 842, fill=1, stroke=0); canvas.setStrokeColor(HexColor("#cbd5e1")); canvas.setLineWidth(.8)
    legal = setting("business_legal_name", "") or "ΕΠΩΝΥΜΙΑ ΕΠΙΧΕΙΡΗΣΗΣ"; activity = setting("business_activity", ""); issuer_vat = setting("business_vat", ""); doy = setting("business_doy", ""); address = setting("business_address", ""); contact = " · ".join(item for item in [setting("business_email", ""), setting("business_phone", ""), setting("business_website", "")] if item); gemi = setting("business_gemi", ""); logo_path = setting("business_logo", "")
    if logo_path and os.path.isfile(logo_path): canvas.drawImage(logo_path, 476, 735, width=64, height=64, preserveAspectRatio=True, mask="auto")
    text_x = 42; canvas.setFillColor(navy); canvas.setFont("SiraSans", 16); canvas.drawString(text_x, 795, legal); canvas.setFillColor(slate); canvas.setFont("SiraSans", 9)
    vat_doy_gemi = " · ".join(part for part in [f"ΑΦΜ: {issuer_vat}" if issuer_vat else "", f"ΔΟΥ: {doy}" if doy else "", f"Αρ. ΓΕΜΗ: {gemi}" if gemi else ""] if part)
    for position, line in enumerate([activity, vat_doy_gemi, address, contact]):
        if line: canvas.drawString(text_x, 775 - position * 13, line)
    canvas.setFont("SiraSans", 8); canvas.setFillColor(pale)
    for x, width in [(42, 250), (300, 62), (370, 86), (464, 88)]: canvas.rect(x, 665, width, 48, fill=1, stroke=1)
    canvas.setFillColor(navy); canvas.drawString(52, 695, "Είδος Παραστατικού"); canvas.drawString(52, 678, INVOICE_TYPES.get(invoice.invoice_type, invoice.invoice_type)[:38]); canvas.drawString(310, 695, "Σειρά"); canvas.drawString(310, 678, setting("invoice_series", "A")); canvas.drawString(380, 695, "Αριθμός"); canvas.drawString(380, 678, invoice.number); canvas.drawString(474, 695, "Ημερομηνία"); canvas.drawString(474, 678, invoice.issue_date.strftime('%d/%m/%Y'))
    canvas.setFillColor(navy); canvas.rect(42, 630, 510, 22, fill=1, stroke=0); canvas.setFillColor(HexColor("#ffffff")); canvas.setFont("SiraSans", 10); canvas.drawString(54, 638, "Στοιχεία Πελάτη")
    saved_client = Client.query.filter_by(vat_number=invoice.vat_number).first()
    customer_address = invoice.customer_address or (saved_client.address if saved_client else "")
    customer_profession = invoice.customer_profession or (saved_client.profession if saved_client else "")
    canvas.setFillColor(HexColor("#ffffff")); canvas.rect(42, 545, 510, 85, fill=1, stroke=1); canvas.setFillColor(navy); canvas.setFont("SiraSans", 11); canvas.drawString(54, 606, invoice.customer); canvas.setFont("SiraSans", 9); canvas.drawString(54, 587, f"ΑΦΜ: {invoice.vat_number}");
    if customer_address: canvas.drawString(54, 570, f"ΔΙΕΥΘΥΝΣΗ: {customer_address.replace(chr(10), ', ')[:78]}")
    if customer_profession: canvas.drawString(54, 557, customer_profession[:90])
    y = 510; canvas.setFillColor(navy); canvas.rect(42, y, 510, 26, fill=1, stroke=0); canvas.setFillColor(HexColor("#ffffff")); canvas.drawString(52, y+9, "Α/Α"); canvas.drawString(82, y+9, "ΠΕΡΙΓΡΑΦΗ"); canvas.drawRightString(300, y+9, "ΠΟΣ."); canvas.drawRightString(350, y+9, "ΤΙΜΗ"); canvas.drawRightString(405, y+9, "ΚΑΘ."); canvas.drawRightString(445, y+9, "ΦΠΑ%"); canvas.drawRightString(490, y+9, "ΦΠΑ €"); canvas.drawRightString(540, y+9, "ΣΥΝΟΛΟ")
    line_net_total, line_vat_total = Decimal("0"), Decimal("0")
    for index, line in enumerate(pdf_lines, 1):
        vat_rate = Decimal(getattr(line, "vat_rate", invoice.vat_rate)); vat_amount = Decimal(line.net) * vat_rate / 100; line_net_total += Decimal(line.net); line_vat_total += vat_amount; y -= 30; canvas.setFillColor(HexColor("#ffffff" if index % 2 else "#f8fafc")); canvas.rect(42, y, 510, 30, fill=1, stroke=1); canvas.setFillColor(navy); canvas.drawString(52, y+10, str(index)); canvas.drawString(82, y+10, str(line.description)[:30]); canvas.drawRightString(300, y+10, f"{Decimal(getattr(line, 'quantity', 1)):g}"); canvas.drawRightString(350, y+10, f"{Decimal(getattr(line, 'unit_price', line.net)):.2f}"); canvas.drawRightString(405, y+10, f"{line.net:.2f}"); canvas.drawRightString(445, y+10, f"{vat_rate:.0f}%"); canvas.drawRightString(490, y+10, f"{vat_amount:.2f}"); canvas.drawRightString(540, y+10, f"{Decimal(line.net)+vat_amount:.2f} €")
    totals_y = 170; canvas.setFillColor(pale); canvas.rect(330, totals_y, 222, 82, fill=1, stroke=1); canvas.setFillColor(navy); canvas.setFont("SiraSans", 10); canvas.drawString(344, totals_y+58, "ΚΑΘΑΡΗ ΑΞΙΑ"); canvas.drawRightString(538, totals_y+58, f"{line_net_total:.2f} €"); canvas.drawString(344, totals_y+37, "Φ.Π.Α."); canvas.drawRightString(538, totals_y+37, f"{line_vat_total:.2f} €"); canvas.setFont("SiraSans", 12); canvas.drawString(344, totals_y+14, "ΣΥΝΟΛΙΚΟ ΠΟΣΟ"); canvas.drawRightString(538, totals_y+14, f"{line_net_total + line_vat_total:.2f} €")
    canvas.setFont("SiraSans", 9); canvas.setFillColor(slate); canvas.drawString(42, 235, f"Τρόπος πληρωμής: {PAYMENT_METHODS.get(invoice.payment_method, '-')}"); canvas.drawString(42, 216, f"UID: {invoice.invoice_uid or '-'}"); canvas.drawString(42, 197, f"ΜΑΡΚ: {invoice.mydata_mark or '-'}")
    if invoice.notes:
        canvas.setFont("SiraSans", 8); canvas.setFillColor(slate); canvas.drawString(155, 150, "Παρατηρήσεις:")
        for index, note_line in enumerate([invoice.notes[i:i+65] for i in range(0, len(invoice.notes), 65)][:3]): canvas.drawString(155, 136 - index * 11, note_line)
    if invoice.qr_url:
        widget = qr.QrCodeWidget(invoice.qr_url); left, bottom, right, top = widget.getBounds(); size = 94; drawing = Drawing(size, size); drawing.add(widget); drawing.transform = [size / (right-left), 0, 0, size / (top-bottom), 0, 0]; renderPDF.draw(drawing, canvas, 42, 85); canvas.linkURL(invoice.qr_url, (42, 85, 136, 179), relative=0)
    canvas.setFillColor(slate); canvas.setFont("SiraSans", 8); canvas.drawString(42, 55, "Το παρόν διαβιβάστηκε επιτυχώς στο myDATA της ΑΑΔΕ." if invoice.mydata_mark else "Πρόχειρο — δεν έχει ακόμη διαβιβαστεί στο myDATA."); canvas.save(); audit("pdf_generated", f"Invoice {invoice.number}"); return send_file(path, as_attachment=False, download_name=f"invoice-{invoice.number}.pdf", mimetype="application/pdf")

@app.route("/invoices/new", methods=["GET", "POST"])
def new_invoice():
    if request.method == "POST":
        invoice_type = request.form["invoice_type"]
        if invoice_type not in INVOICE_TYPES: flash("Invalid AADE invoice type.", "error"); return redirect(url_for("new_invoice"))
        payment_method = request.form.get("payment_method", "3")
        if payment_method not in PAYMENT_METHODS: flash("Choose a valid AADE payment method.", "error"); return redirect(url_for("new_invoice"))
        retail = invoice_type in {"11.1", "11.2", "11.3", "11.4", "11.5"}
        default_income_category = "category1_3"
        default_income_type = "E3_561_003" if retail else "E3_561_001"
        descriptions, quantities, unit_prices, rates, reasons = request.form.getlist("line_description"), request.form.getlist("line_quantity"), request.form.getlist("line_unit_price"), request.form.getlist("line_vat_rate"), request.form.getlist("line_vat_exemption_reason")
        income_categories, income_types = request.form.getlist("line_income_category"), request.form.getlist("line_income_type")
        try:
            parsed = [(description.strip(), Decimal(quantity), Decimal(unit_price), Decimal(quantity) * Decimal(unit_price), Decimal(rate), reason if Decimal(rate) == 0 else None, category or default_income_category, income_type or default_income_type) for description, quantity, unit_price, rate, reason, category, income_type in zip(descriptions, quantities, unit_prices, rates, reasons, income_categories, income_types)]
            if not parsed or any(not description or quantity <= 0 or unit_price < 0 or (rate == 0 and reason not in VAT_EXEMPTION_REASONS) for description, quantity, unit_price, _, rate, reason, _, _ in parsed) or any(category not in INCOME_CATEGORIES or income_type not in INCOME_TYPES for _, _, _, _, _, _, category, income_type in parsed): raise ValueError
        except (ValueError, ArithmeticError): flash("Add at least one valid line and an AADE VAT exemption reason for every 0% VAT line.", "error"); return redirect(url_for("new_invoice"))
        total_net, total_vat = sum((net for _, _, _, net, _, _, _, _ in parsed), Decimal("0")), sum((net * rate / 100 for _, _, _, net, rate, _, _, _ in parsed), Decimal("0"))
        customer_address = "" if retail else request.form.get("customer_address", "").strip(); customer_profession = "" if retail else request.form.get("customer_profession", "").strip()
        invoice = Invoice(number=request.form["number"], invoice_type=invoice_type, customer="ΠΕΛΑΤΗΣ ΛΙΑΝΙΚΗΣ" if retail else request.form["customer"], vat_number="000000000" if retail else request.form["vat_number"], customer_address=customer_address, customer_profession=customer_profession, notes=request.form.get("notes", "").strip(), description=parsed[0][0], net=total_net, vat_rate=(total_vat / total_net * 100 if total_net else Decimal("0")), issue_date=date.fromisoformat(request.form["issue_date"]), payment_method=payment_method)
        db.session.add(invoice)
        db.session.flush()
        for description, quantity, unit_price, net, rate, reason, category, income_type in parsed: db.session.add(InvoiceLine(invoice_id=invoice.id, description=description, quantity=quantity, unit_price=unit_price, net=net, vat_rate=rate, vat_exemption_reason=reason, income_category=category, income_type=income_type))
        if request.form["number"].isdigit(): set_setting("invoice_next_number", str(int(request.form["number"]) + 1))
        db.session.commit(); audit("invoice_draft", f"Created {invoice.number}"); flash("Invoice saved as draft.", "success"); return redirect(url_for("invoice_detail", invoice_id=invoice.id))
    priority = ["1.1", "2.1", "11.1", "11.2"]
    ordered_types = dict(sorted(INVOICE_TYPES.items(), key=lambda item: (priority.index(item[0]) if item[0] in priority else 99, item[0])))
    return render_template("invoice_form.html", today=date.today().isoformat(), clients=Client.query.order_by(Client.name).all(), invoice_types=ordered_types, next_number=setting("invoice_next_number", "1"), series=setting("invoice_series", "A"), exemption_reasons=VAT_EXEMPTION_REASONS, income_categories=INCOME_CATEGORIES, income_types=INCOME_TYPES, payment_methods=PAYMENT_METHODS)

@app.get("/invoices/<int:invoice_id>")
def invoice_detail(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    lines = InvoiceLine.query.filter_by(invoice_id=invoice.id).order_by(InvoiceLine.id).all()
    if not lines:
        lines = [type("LegacyLine", (), {"description": invoice.description, "net": invoice.net, "quantity": Decimal("1"), "unit_price": invoice.net, "vat_rate": invoice.vat_rate, "vat_exemption_reason": None, "income_category": None, "income_type": None})()]
    return render_template("invoice_detail.html", invoice=invoice, lines=lines, invoice_type_name=INVOICE_TYPES.get(invoice.invoice_type, "Unknown myDATA type"), payment_method_name=PAYMENT_METHODS.get(invoice.payment_method, "-"), invoice_xml_preview=invoice_xml(invoice).decode("utf-8"))
@app.post("/invoices/<int:invoice_id>/send")
def send_invoice(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    try:
        response = transmit(invoice); invoice.mydata_mark, invoice.invoice_uid, invoice.qr_url, invoice.status = response["mark"], response["uid"], response["qr_url"], "transmitted"; db.session.commit(); flash(f"Submitted successfully — ΜΑΡΚ {invoice.mydata_mark}", "success")
    except (ValueError, requests.RequestException) as error: flash(str(error), "error")
    return redirect(url_for("invoice_detail", invoice_id=invoice.id))
@app.get("/invoices")
def invoices(): return render_template("invoices.html", invoices=Invoice.query.order_by(Invoice.created_at.desc()).all(), invoice_types=INVOICE_TYPES, payment_methods=PAYMENT_METHODS)
@app.post("/invoices/<int:invoice_id>/delete")
def delete_invoice(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    if invoice.status == "transmitted": flash("A transmitted invoice cannot be deleted; cancel it through AADE.", "error")
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
def lookup_gemi(vat):
    headers = {"User-Agent": "Elefthero/1.0 (+https://github.com/achouvardas/Elefthero)", "Accept": "application/json, text/plain, */*", "Accept-Language": "el-GR,el;q=0.9,en;q=0.8"}
    try:
        autocomplete_response = requests.get(f"https://publicity.businessportal.gr/api/autocomplete/{vat}", headers=headers, timeout=10); autocomplete_response.raise_for_status(); autocomplete = autocomplete_response.json()
        matches = autocomplete.get("payload", {}).get("autocomplete", [])
        if not matches or not matches[0].get("arGemi"): audit("gemi_lookup", f"No ΓΕΜΗ record for VAT {vat}", "{}"); return "", "", "", False
        gemi = str(matches[0]["arGemi"])
        details_response = requests.post("https://publicity.businessportal.gr/api/company/details", json={"query": {"arGEMI": gemi}, "token": None, "language": "el"}, headers=headers, timeout=12); details_response.raise_for_status(); details = details_response.json()
        payload = details.get("companyInfo", {}).get("payload", {})
        profession = next((item.get("descr", "").strip() for item in payload.get("kadData", []) if item.get("activities", "").strip().lower() == "κύρια".lower() and item.get("descr")), "")
        address = payload.get("company", {}).get("company_address", "").strip()
        audit("gemi_lookup", f"ΓΕΜΗ {gemi} for VAT {vat}; primary activity: {profession or 'not provided'}", str({"gemi": gemi, "profession": profession, "address": address}))
        return gemi, profession, address, False
    except requests.HTTPError as error:
        response = error.response; status = response.status_code if response is not None else "unknown"; excerpt = response.text[:300] if response is not None else ""; audit("gemi_lookup_failed", f"ΓΕΜΗ lookup for VAT {vat}: HTTP {status}", excerpt); return "", "", "", status == 429
    except (requests.RequestException, ValueError, TypeError, KeyError) as error: audit("gemi_lookup_failed", f"ΓΕΜΗ lookup for VAT {vat}: {error}"); return "", "", "", False
@app.route("/clients", methods=["GET", "POST"])
def clients():
    if request.method == "POST":
        try:
            vat, name, address = check_vies(request.form["vat_number"]); client = Client.query.filter_by(vat_number=vat).first(); now = datetime.utcnow(); lookup_due = not client or ((client.gemi_retry_after and now >= client.gemi_retry_after) or (not client.gemi_retry_after and (not client.gemi_checked_at or now - client.gemi_checked_at >= timedelta(days=30))))
            gemi, profession, gemi_address, rate_limited = lookup_gemi(vat) if lookup_due else ("", "", "", False); address = address or gemi_address
            if client:
                client.name, client.address, client.gemi_number, client.profession, client.vies_checked_at = name, address, gemi or client.gemi_number, profession or client.profession, now
                if lookup_due: client.gemi_checked_at, client.gemi_retry_after = now, (now + timedelta(minutes=5) if rate_limited else None)
            else: db.session.add(Client(name=name, vat_number=vat, address=address, gemi_number=gemi, profession=profession, gemi_checked_at=now, gemi_retry_after=(now + timedelta(minutes=5) if rate_limited else None)))
            db.session.commit(); flash(f"{name} verified with VIES and saved.", "success")
        except (ValueError, requests.RequestException) as error: audit("vies_failed", str(error)); flash(f"VIES validation unavailable: {error}", "error")
        return redirect(url_for("clients"))
    saved_clients = Client.query.order_by(Client.name).all()
    invoice_counts = {}
    for vat_number, count in db.session.query(Invoice.vat_number, func.count(Invoice.id)).group_by(Invoice.vat_number):
        invoice_counts[vat_number] = count
    return render_template("clients.html", clients=saved_clients, invoice_counts=invoice_counts)

@app.get("/clients/<int:client_id>/invoices")
def client_invoices(client_id):
    client = db.get_or_404(Client, client_id)
    start_raw, end_raw = request.args.get("start", ""), request.args.get("end", "")
    try:
        start_date = date.fromisoformat(start_raw) if start_raw else None
        end_date = date.fromisoformat(end_raw) if end_raw else None
    except ValueError:
        flash("Use valid dates for the client invoice filter.", "error")
        return redirect(url_for("client_invoices", client_id=client.id))
    if start_date and end_date and start_date > end_date:
        flash("The start date must be before the end date.", "error")
        return redirect(url_for("client_invoices", client_id=client.id))
    query = Invoice.query.filter_by(vat_number=client.vat_number)
    if start_date: query = query.filter(Invoice.issue_date >= start_date)
    if end_date: query = query.filter(Invoice.issue_date <= end_date)
    client_invoice_rows = query.order_by(Invoice.issue_date.desc(), Invoice.created_at.desc()).all()
    net_total = sum((invoice.net for invoice in client_invoice_rows), Decimal("0"))
    vat_total = sum((invoice.vat_amount for invoice in client_invoice_rows), Decimal("0"))
    gross_total = net_total + vat_total
    return render_template("client_invoices.html", client=client, invoices=client_invoice_rows, start_date=start_raw, end_date=end_raw, net_total=net_total, vat_total=vat_total, gross_total=gross_total)
@app.post("/clients/<int:client_id>/delete")
def delete_client(client_id):
    client = db.get_or_404(Client, client_id); db.session.delete(client); db.session.commit(); audit("client_deleted", client.vat_number); flash("Client deleted.", "success"); return redirect(url_for("clients"))
@app.post("/locale/<code>")
def set_locale(code): session["locale"] = code if code in COPY else "en"; return redirect(request.referrer or url_for("dashboard"))
@app.get("/health")
def health(): return jsonify(status="ok", mode=current_mode(), database="sqlite")

with app.app_context():
    db.create_all()
    existing_columns = {column["name"] for column in inspect(db.engine).get_columns("invoice_line")}
    for name, definition in {"income_category": "VARCHAR(30)", "income_type": "VARCHAR(30)", "quantity": "NUMERIC(12,3) DEFAULT 1", "unit_price": "NUMERIC(12,2) DEFAULT 0"}.items():
        if name not in existing_columns: db.session.execute(text(f"ALTER TABLE invoice_line ADD COLUMN {name} {definition}"))
    db.session.execute(text("UPDATE invoice_line SET quantity = 1 WHERE quantity IS NULL OR quantity = 0"))
    db.session.execute(text("UPDATE invoice_line SET unit_price = net WHERE unit_price IS NULL OR unit_price = 0"))
    invoice_columns = {column["name"] for column in inspect(db.engine).get_columns("invoice")}
    for name, definition in {"payment_method": "VARCHAR(2) DEFAULT '3'", "invoice_uid": "VARCHAR(80)", "qr_url": "TEXT", "customer_address": "VARCHAR(300)", "customer_profession": "VARCHAR(300)", "notes": "TEXT"}.items():
        if name not in invoice_columns: db.session.execute(text(f"ALTER TABLE invoice ADD COLUMN {name} {definition}"))
    client_columns = {column["name"] for column in inspect(db.engine).get_columns("client")}
    for name, definition in {"profession": "VARCHAR(300)", "gemi_number": "VARCHAR(30)", "gemi_checked_at": "DATETIME", "gemi_retry_after": "DATETIME"}.items():
        if name not in client_columns: db.session.execute(text(f"ALTER TABLE client ADD COLUMN {name} {definition}"))
    configured_mode = setting("mydata_mode", "")
    if configured_mode and configured_mode not in ENVIRONMENTS: set_setting("mydata_mode", "test")
    db.session.commit()
if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", host="127.0.0.1", port=int(os.getenv("PORT", "5000")))
