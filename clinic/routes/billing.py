from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
from clinic.extensions import db
from clinic.models import Patient, Invoice, InvoiceItem, Payment
from clinic.utils import generate_invoice_number
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

billing_bp = Blueprint("billing_bp", __name__, url_prefix="/billing")


# ---------------- SECURE FETCH ----------------
def get_secure_invoice(id):
    return (
        Invoice.query
        .join(Patient)
        .filter(
            Invoice.id == id,
            Patient.user_id == session["user_id"]
        )
        .first_or_404()
    )


# ---------------- DASHBOARD ----------------
from sqlalchemy import or_

@billing_bp.route("/", methods=["GET"])
def billing():
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    q = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()

    # Base query (secure per doctor)
    query = (
        Invoice.query
        .join(Patient)
        .filter(Patient.user_id == session["user_id"])
    )

    # 🔍 Search by patient name OR invoice number
    if q:
        query = query.filter(
            or_(
                Patient.name.ilike(f"%{q}%"),
                Invoice.invoice_number.ilike(f"%{q}%")
            )
        )

    # ✅ Status filter (exact match)
    if status:
        query = query.filter(Invoice.status == status)

    # Final ordering
    invoices = query.order_by(Invoice.created_at.desc()).all()

    # Due invoices count
    due_count = (
        Invoice.query
        .join(Patient)
        .filter(
            Patient.user_id == session["user_id"],
            Invoice.status != "Paid"
        )
        .count()
    )

    return render_template(
        "billing/billing.html",
        invoices=invoices,
        due_count=due_count
    )



# ---------------- CREATE INVOICE ----------------
@billing_bp.route("/create_invoice", methods=["GET", "POST"])
def create_invoice():
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    patients = Patient.query.filter_by(user_id=session["user_id"]).all()

    if request.method == "POST":
        invoice = Invoice(
            patient_id=request.form["patient_id"],
            invoice_number=generate_invoice_number(session["user_id"]),
            created_at=datetime.utcnow(),
            description=request.form.get("description", ""),
            total_amount=float(request.form.get("total_amount", 0)),
            status="Unpaid",
            is_locked=False
        )
        db.session.add(invoice)
        db.session.commit()

        for name, amt in zip(
            request.form.getlist("item_name[]"),
            request.form.getlist("item_amount[]")
        ):
            if name.strip():
                db.session.add(
                    InvoiceItem(
                        invoice_id=invoice.id,
                        item_name=name.strip(),
                        amount=float(amt or 0)
                    )
                )

        db.session.commit()
        flash("Invoice created.", "success")
        return redirect(url_for("billing_bp.billing"))

    return render_template("billing/create_invoice.html", patients=patients)


# ---------------- VIEW ----------------
@billing_bp.route("/view/<int:id>")
def view_invoice(id):
    inv = get_secure_invoice(id)
    paid = sum(p.amount for p in inv.payments)
    balance = inv.total_amount - paid
    return render_template("billing/view_invoice.html", inv=inv, paid=paid, balance=balance)


# ---------------- EDIT (BLOCKED IF LOCKED) ----------------
@billing_bp.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_invoice(id):
    inv = get_secure_invoice(id)

    if inv.is_locked:
        flash("Invoice locked after payment.", "danger")
        return redirect(url_for("billing_bp.view_invoice", id=id))

    if request.method == "POST":
        inv.description = request.form.get("description", "")
        inv.total_amount = float(request.form.get("total_amount", 0))

        InvoiceItem.query.filter_by(invoice_id=inv.id).delete()
        for name, amt in zip(
            request.form.getlist("item_name[]"),
            request.form.getlist("item_amount[]")
        ):
            if name.strip():
                db.session.add(
                    InvoiceItem(
                        invoice_id=inv.id,
                        item_name=name.strip(),
                        amount=float(amt or 0)
                    )
                )

        db.session.commit()
        flash("Invoice updated.", "success")
        return redirect(url_for("billing_bp.view_invoice", id=id))

    patients = Patient.query.filter_by(user_id=session["user_id"]).all()
    return render_template("billing/edit_invoice.html", inv=inv, patients=patients)


# ---------------- DELETE (BLOCKED IF LOCKED) ----------------
@billing_bp.route("/delete/<int:id>")
def delete_invoice(id):
    inv = get_secure_invoice(id)

    if inv.is_locked:
        flash("Locked invoices cannot be deleted.", "danger")
        return redirect(url_for("billing_bp.billing"))

    InvoiceItem.query.filter_by(invoice_id=inv.id).delete()
    Payment.query.filter_by(invoice_id=inv.id).delete()
    db.session.delete(inv)
    db.session.commit()

    flash("Invoice deleted.", "warning")
    return redirect(url_for("billing_bp.billing"))


# ---------------- ADD PAYMENT (EXACT ONLY) ----------------
@billing_bp.route("/add_payment/<int:id>", methods=["POST"])
def add_payment(id):
    inv = get_secure_invoice(id)

    # 🚫 Block if already paid
    if inv.is_locked:
        flash("Invoice already fully paid.", "warning")
        return redirect(url_for("billing_bp.view_invoice", id=id))

    try:
        amt = float(request.form.get("amount", 0))
    except ValueError:
        flash("Invalid amount.", "danger")
        return redirect(url_for("billing_bp.view_invoice", id=id))

    if amt <= 0:
        flash("Invalid amount.", "danger")
        return redirect(url_for("billing_bp.view_invoice", id=id))

    paid_so_far = sum(p.amount for p in inv.payments)
    remaining = inv.total_amount - paid_so_far

    # ❌ enforce exact payment
    if abs(amt - remaining) > 0.01:
        flash(f"You must pay the exact remaining amount: ₹ {remaining:.2f}", "danger")
        return redirect(url_for("billing_bp.view_invoice", id=id))

    # ✅ record payment
    payment = Payment(
        invoice_id=inv.id,
        amount=amt,
        paid_at=datetime.utcnow()
    )
    db.session.add(payment)

    # ✅ mark invoice as paid & lock
    inv.status = "Paid"
    inv.is_locked = True

    db.session.commit()

    flash("Invoice paid successfully.", "success")
    return redirect(url_for("billing_bp.view_invoice", id=id))

# ---------------- DOWNLOAD PDF ----------------
@billing_bp.route("/download/<int:id>")
def download_invoice(id):
    inv = get_secure_invoice(id)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, "Invoice")

    y -= 25
    pdf.setFont("Helvetica", 11)
    pdf.drawString(40, y, f"Invoice No: {inv.invoice_number}")
    y -= 15
    pdf.drawString(40, y, f"Patient: {inv.patient.name}")

    y -= 25
    for item in inv.items:
        pdf.drawString(40, y, item.item_name)
        pdf.drawRightString(width - 40, y, f"₹{item.amount:.2f}")
        y -= 15

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y, "Total")
    pdf.drawRightString(width - 40, y, f"₹{inv.total_amount:.2f}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Invoice_{inv.invoice_number}.pdf",
        mimetype="application/pdf"
    )
