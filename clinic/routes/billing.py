from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from clinic.extensions import db
from clinic.models import Patient, Invoice, InvoiceItem, Payment, User
from clinic.utils import generate_invoice_number
from datetime import datetime

billing_bp = Blueprint("billing_bp", __name__, url_prefix="/billing")


# ------------------------------------------------
# SECURE INVOICE FETCH
# ------------------------------------------------
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


# ------------------------------------------------
# BILLING DASHBOARD
# ------------------------------------------------
@billing_bp.route("/", methods=["GET"])
def billing():
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    q = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()

    invoices = (
        Invoice.query
        .join(Patient)
        .filter(Patient.user_id == session["user_id"])
        .order_by(Invoice.created_at.desc())
    )

    if q:
        invoices = invoices.filter(
            (Patient.name.ilike(f"%{q}%")) |
            (Invoice.invoice_number.ilike(f"%{q}%"))
        )

    if status:
        invoices = invoices.filter(Invoice.status == status)

    invoices = invoices.all()

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


# ------------------------------------------------
# CREATE INVOICE
# ------------------------------------------------
@billing_bp.route("/create_invoice", methods=["GET", "POST"])
def create_invoice():
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    patients = Patient.query.filter_by(
        user_id=session["user_id"]
    ).order_by(Patient.name).all()

    if request.method == "POST":
        patient = Patient.query.filter_by(
            id=int(request.form["patient_id"]),
            user_id=session["user_id"]
        ).first_or_404()

        description = request.form.get("description", "")
        total = float(request.form.get("total_amount", 0) or 0)

        invoice = Invoice(
            patient_id=patient.id,
            invoice_number=generate_invoice_number(),
            description=description,
            total_amount=total,
            created_at=datetime.utcnow(),
            status="Unpaid",
            is_locked=False
        )

        db.session.add(invoice)
        db.session.commit()

        # ---------- ITEMS ----------
        names = request.form.getlist("item_name[]")
        amounts = request.form.getlist("item_amount[]")

        for name, amt in zip(names, amounts):
            if not name.strip():
                continue
            db.session.add(
                InvoiceItem(
                    invoice_id=invoice.id,
                    item_name=name.strip(),
                    amount=float(amt or 0)
                )
            )

        db.session.commit()

        # ---------- OPTIONAL INITIAL PAYMENT ----------
        paid_now = float(request.form.get("paid_now", 0) or 0)
        if paid_now > 0:
            payment = Payment(
                invoice_id=invoice.id,
                amount=paid_now,
                paid_at=datetime.utcnow()
            )
            db.session.add(payment)
            db.session.commit()

            if abs(paid_now - invoice.total_amount) < 0.001:
                invoice.status = "Paid"
                invoice.is_locked = True
            else:
                invoice.status = "Partial"

            db.session.commit()

        flash("Invoice created successfully.", "success")
        return redirect(url_for("billing_bp.billing"))

    return render_template(
        "billing/create_invoice.html",
        patients=patients
    )


# ------------------------------------------------
# VIEW INVOICE
# ------------------------------------------------
@billing_bp.route("/view/<int:id>", methods=["GET"])
def view_invoice(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    inv = get_secure_invoice(id)
    paid = sum(p.amount for p in inv.payments)
    balance = inv.total_amount - paid

    return render_template(
        "billing/view_invoice.html",
        inv=inv,
        paid=paid,
        balance=balance
    )


# ------------------------------------------------
# DELETE INVOICE (BLOCK IF LOCKED)
# ------------------------------------------------
@billing_bp.route("/delete/<int:id>", methods=["GET"])
def delete_invoice(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    inv = get_secure_invoice(id)

    if inv.is_locked:
        flash("Paid invoices cannot be deleted.", "danger")
        return redirect(url_for("billing_bp.billing"))

    InvoiceItem.query.filter_by(invoice_id=inv.id).delete()
    Payment.query.filter_by(invoice_id=inv.id).delete()

    db.session.delete(inv)
    db.session.commit()

    flash("Invoice deleted.", "warning")
    return redirect(url_for("billing_bp.billing"))


# ------------------------------------------------
# EDIT INVOICE (BLOCK IF LOCKED)
# ------------------------------------------------
@billing_bp.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_invoice(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    inv = get_secure_invoice(id)

    if inv.is_locked:
        flash("Paid invoices cannot be edited.", "danger")
        return redirect(url_for("billing_bp.view_invoice", id=inv.id))

    patients = Patient.query.filter_by(
        user_id=session["user_id"]
    ).order_by(Patient.name).all()

    if request.method == "POST":
        inv.patient_id = int(request.form["patient_id"])
        inv.description = request.form.get("description", "")
        inv.total_amount = float(request.form.get("total_amount", 0) or 0)
        db.session.commit()

        InvoiceItem.query.filter_by(invoice_id=inv.id).delete()

        names = request.form.getlist("item_name[]")
        amounts = request.form.getlist("item_amount[]")

        for name, amt in zip(names, amounts):
            if not name.strip():
                continue
            db.session.add(
                InvoiceItem(
                    invoice_id=inv.id,
                    item_name=name.strip(),
                    amount=float(amt or 0)
                )
            )

        db.session.commit()

        flash("Invoice updated.", "success")
        return redirect(url_for("billing_bp.view_invoice", id=inv.id))

    return render_template(
        "billing/edit_invoice.html",
        inv=inv,
        patients=patients
    )


# ------------------------------------------------
# ADD PAYMENT (BLOCK IF ALREADY PAID)
# ------------------------------------------------
@billing_bp.route("/add_payment/<int:id>", methods=["POST"])
def add_payment(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    inv = get_secure_invoice(id)

    if inv.is_locked:
        flash("Invoice already fully paid.", "warning")
        return redirect(url_for("billing_bp.view_invoice", id=id))

    amt = float(request.form.get("amount", 0) or 0)
    method = request.form.get("method", "Cash")

    if amt <= 0:
        flash("Enter valid amount.", "danger")
        return redirect(url_for("billing_bp.view_invoice", id=id))

    payment = Payment(
        invoice_id=inv.id,
        amount=amt,
        method=method,
        paid_at=datetime.utcnow()
    )

    db.session.add(payment)
    db.session.commit()

    paid = sum(p.amount for p in inv.payments)
    if abs(paid - inv.total_amount) < 0.001:
        inv.status = "Paid"
        inv.is_locked = True
    elif paid > 0:
        inv.status = "Partial"
    else:
        inv.status = "Unpaid"

    db.session.commit()

    flash("Payment recorded.", "success")
    return redirect(url_for("billing_bp.view_invoice", id=id))

# ------------------------------------------------
# DOWNLOAD INVOICE
# ------------------------------------------------
@billing_bp.route("/download/<int:id>")
def download_invoice(id):
    flash("PDF download coming soon.", "info")
    return redirect(url_for("billing_bp.view_invoice", id=id))