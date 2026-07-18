import os
import uuid
from datetime import date, datetime
from decimal import Decimal
from xml.etree.ElementTree import Element, SubElement, fromstring, tostring

import requests
from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy

load_dotenv()
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "unsafe-local-development-key"),
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///myaade.sqlite3"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
db = SQLAlchemy(app)

ENVIRONMENTS = {
    "demo": {"label": "Demo", "url": None, "safe": True},
    "development": {"label": "AADE Test", "url": "https://mydataapidev.aade.gr", "safe": False},
    "production": {"label": "AADE Production", "url": "https://mydatapi.aade.gr/myDATA", "safe": False},
}
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

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    vat_number = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.String(300))
    vies_checked_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

def locale(): return session.get("locale", "en")
@app.context_processor
def inject_ui(): return {"t": COPY[locale()], "locale": locale(), "mode": current_mode()}
def current_mode(): return os.getenv("MYDATA_MODE", "demo").lower()

def invoice_xml(invoice):
    root = Element("InvoicesDoc")
    inv = SubElement(root, "invoice")
    header = SubElement(inv, "invoiceHeader")
    SubElement(header, "series").text, SubElement(header, "aa").text = "A", invoice.number
    SubElement(header, "issueDate").text, SubElement(header, "invoiceType").text = invoice.issue_date.isoformat(), invoice.invoice_type
    issuer, counterpart = SubElement(inv, "issuer"), SubElement(inv, "counterpart")
    SubElement(issuer, "vatNumber").text = os.getenv("MYDATA_VAT_NUMBER", "")
    SubElement(counterpart, "vatNumber").text = invoice.vat_number
    details = SubElement(inv, "invoiceDetails")
    SubElement(details, "lineNumber").text, SubElement(details, "netValue").text = "1", f"{invoice.net:.2f}"
    SubElement(details, "vatCategory").text, SubElement(details, "vatAmount").text = "1", f"{invoice.vat_amount:.2f}"
    summary = SubElement(inv, "invoiceSummary")
    SubElement(summary, "totalNetValue").text, SubElement(summary, "totalVatAmount").text = f"{invoice.net:.2f}", f"{invoice.vat_amount:.2f}"
    SubElement(summary, "totalGrossValue").text = f"{invoice.total:.2f}"
    return tostring(root, encoding="utf-8", xml_declaration=True)

def transmit(invoice):
    mode = current_mode()
    if mode == "demo": return "DEMO-" + uuid.uuid4().hex[:10].upper()
    config = ENVIRONMENTS.get(mode)
    user, key = os.getenv("MYDATA_USER_ID"), os.getenv("MYDATA_SUBSCRIPTION_KEY")
    if not config or not user or not key: raise ValueError("AADE credentials are missing. Add them only to your local environment.")
    response = requests.post(config["url"] + "/SendInvoices", data=invoice_xml(invoice), headers={"aade-user-id": user, "ocp-apim-subscription-key": key, "Content-Type": "application/xml"}, timeout=20)
    response.raise_for_status()
    return "AADE-" + uuid.uuid4().hex[:10].upper() # Response parsing is deliberately surfaced in Activity until AADE schema validation.

@app.get("/")
def dashboard():
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    total = sum((i.total for i in invoices if i.status == "transmitted"), Decimal("0"))
    return render_template("dashboard.html", invoices=invoices[:5], total=total, drafts=sum(i.status == "draft" for i in invoices))

@app.route("/invoices/new", methods=["GET", "POST"])
def new_invoice():
    if request.method == "POST":
        invoice_type = request.form["invoice_type"]
        if invoice_type not in INVOICE_TYPES: flash("Invalid AADE invoice type.", "error"); return redirect(url_for("new_invoice"))
        invoice = Invoice(number=request.form["number"], invoice_type=invoice_type, customer=request.form["customer"], vat_number=request.form["vat_number"], description=request.form["description"], net=Decimal(request.form["net"]), vat_rate=Decimal(request.form["vat_rate"]), issue_date=date.fromisoformat(request.form["issue_date"]))
        db.session.add(invoice); db.session.commit(); flash("Invoice saved as draft.", "success"); return redirect(url_for("invoice_detail", invoice_id=invoice.id))
    return render_template("invoice_form.html", today=date.today().isoformat(), clients=Client.query.order_by(Client.name).all(), invoice_types=INVOICE_TYPES)

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
def check_vies(raw_vat):
    vat = "".join(char for char in raw_vat.upper().replace("GR", "") if char.isalnum())
    if not vat.isdigit() or len(vat) != 9: raise ValueError("Enter a 9-digit Greek VAT number.")
    payload = f'<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:ec.europa.eu:taxud:vies:services:checkVat:types"><soapenv:Body><urn:checkVat><urn:countryCode>GR</urn:countryCode><urn:vatNumber>{vat}</urn:vatNumber></urn:checkVat></soapenv:Body></soapenv:Envelope>'
    response = requests.post("https://ec.europa.eu/taxation_customs/vies/services/checkVatService", data=payload.encode(), headers={"Content-Type": "text/xml; charset=utf-8"}, timeout=12); response.raise_for_status()
    fields = {node.tag.rsplit("}", 1)[-1]: (node.text or "").strip() for node in fromstring(response.content).iter()}
    if fields.get("valid", "false").lower() != "true": raise ValueError("VIES could not validate this Greek VAT number.")
    return vat, fields.get("name", "Verified Greek business"), fields.get("address", "")
@app.route("/clients", methods=["GET", "POST"])
def clients():
    if request.method == "POST":
        try:
            vat, name, address = check_vies(request.form["vat_number"]); client = Client.query.filter_by(vat_number=vat).first()
            if client: client.name, client.address, client.vies_checked_at = name, address, datetime.utcnow()
            else: db.session.add(Client(name=name, vat_number=vat, address=address))
            db.session.commit(); flash(f"{name} verified with VIES and saved.", "success")
        except (ValueError, requests.RequestException) as error: flash(f"VIES validation unavailable: {error}", "error")
        return redirect(url_for("clients"))
    return render_template("clients.html", clients=Client.query.order_by(Client.name).all())
@app.post("/locale/<code>")
def set_locale(code): session["locale"] = code if code in COPY else "en"; return redirect(request.referrer or url_for("dashboard"))
@app.get("/health")
def health(): return jsonify(status="ok", mode=current_mode(), database="sqlite")

with app.app_context(): db.create_all()
if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", host="127.0.0.1", port=int(os.getenv("PORT", "5000")))
