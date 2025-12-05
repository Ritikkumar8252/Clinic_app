import random
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, send_file
)
from datetime import datetime
from ..extensions import db
from ..models import Invoice, Payment, Patient

billing_bp = Blueprint("billing_bp", __name__)


def generate_invoice_number():
    return f"INV{random.randint(100000, 999999)}"


@billing_bp.route("/billing")
def billing():
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    invoices = Invoice.query.order_by(Invoice.id.desc()).all()
    due_count = Invoice.query.filter(Invoice.status != "Paid").count()

    return render_template("billing.html", invoices=invoices, due_count=due_count)


@billing_bp.route("/create_invoice", methods=["GET", "POST"])
def create_invoice():
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    patients = Patient.query.all()

    if request.method == "POST":
        invoice = Invoice(
            patient_id=int(request.form["patient_id"]),
            invoice_number=generate_invoice_number(),
            description=request.form.get("description", ""),
            total_amount=float(request.form.get("total_amount", 0)),
            due_date=request.form.get("due_date", ""),
            status="Unpaid",
            created_at=datetime.now().strftime("%Y-%m-%d")
        )

        db.session.add(invoice)
        db.session.commit()
        flash("Invoice created.")
        return redirect(url_for("billing_bp.billing"))

    return render_template("create_invoice.html", patients=patients)


@billing_bp.route("/view_invoice/<int:id>")
def view_invoice(id):
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    invoice = Invoice.query.get_or_404(id)
    paid = sum(p.amount for p in invoice.payments)
    balance = invoice.total_amount - paid

    return render_template("view_invoice.html", invoice=invoice, paid=paid, balance=balance)


@billing_bp.route("/pay_invoice/<int:id>", methods=["POST"])
def pay_invoice(id):
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    invoice = Invoice.query.get_or_404(id)
    amount = float(request.form.get("amount", 0))
    method = request.form.get("method", "Cash")

    payment = Payment(
        invoice_id=invoice.id,
        amount=amount,
        method=method,
        paid_at=datetime.now().strftime("%Y-%m-%d")
    )

    db.session.add(payment)

    paid_total = sum(p.amount for p in invoice.payments) + amount
    invoice.status = "Paid" if paid_total >= invoice.total_amount else "Partial"

    db.session.commit()
    flash("Payment recorded.")
    return redirect(url_for("billing_bp.view_invoice", id=id))


@billing_bp.route("/delete_invoice/<int:id>")
def delete_invoice(id):
    invoice = Invoice.query.get_or_404(id)

    for p in invoice.payments:
        db.session.delete(p)

    db.session.delete(invoice)
    db.session.commit()
    flash("Invoice deleted.")
    return redirect(url_for("billing_bp.billing"))


@billing_bp.route("/download_invoice/<int:id>")
def download_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    patient = invoice.patient
    paid = sum(p.amount for p in invoice.payments)
    balance = invoice.total_amount - paid

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 16)
    p.drawString(40, height - 50, "ClinicApp Invoice")
    p.setFont("Helvetica", 10)
    p.drawString(40, height - 80, f"Invoice No: {invoice.invoice_number}")
    p.drawString(40, height - 95, f"Date: {invoice.created_at}")
    p.drawString(40, height - 110, f"Patient: {patient.name if patient else 'N/A'}")

    p.drawString(40, height - 150, "Description")
    p.drawString(350, height - 150, "Amount")
    p.drawString(40, height - 170, invoice.description or "—")
    p.drawString(350, height - 170, f"{invoice.total_amount:.2f}")

    p.drawString(40, height - 210, f"Paid: {paid:.2f}")
    p.drawString(40, height - 225, f"Balance: {balance:.2f}")
    p.drawString(40, height - 245, f"Status: {invoice.status}")

    p.showPage()
    p.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"invoice_{invoice.invoice_number}.pdf", mimetype="application/pdf")
