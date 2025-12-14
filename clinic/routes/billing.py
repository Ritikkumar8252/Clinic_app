from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, make_response
from clinic.extensions import db
from clinic.models import Patient, Invoice, InvoiceItem, Payment,User
from datetime import datetime
import io

billing_bp = Blueprint("billing_bp", __name__, url_prefix="/billing")


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


# helper: generate next invoice number
def next_invoice_number():
    last = Invoice.query.order_by(Invoice.id.desc()).first()
    if last:
        return f"INV-{last.id + 1:04}"
    return "INV-0001"

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
        invoices = invoices.filter((Patient.name.ilike(f"%{q}%")) | (Invoice.invoice_number.ilike(f"%{q}%")))

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


    return render_template("billing/billing.html", invoices=invoices, due_count=due_count)

@billing_bp.route("/create_invoice", methods=["GET", "POST"])
def create_invoice():
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    patients = Patient.query.filter_by(
        user_id=session["user_id"]
    ).order_by(Patient.name).all()

    new_invoice_number = next_invoice_number()

    if request.method == "POST":
        # patient validation
        patient = Patient.query.filter_by(
            id=int(request.form["patient_id"]),
            user_id=session["user_id"]
        ).first_or_404()

        invoice_number = request.form.get("invoice_number", new_invoice_number)
        description = request.form.get("description", "")
        total = float(request.form.get("total_amount", 0) or 0)

        # ✅ FIX 1: store real datetime, NOT string
        invoice = Invoice(
            patient_id=patient.id,
            invoice_number=invoice_number,
            description=description,
            total_amount=total,
            created_at=datetime.now(),
            status="Unpaid"
        )

        db.session.add(invoice)
        db.session.commit()   # invoice.id needed for items

        # ✅ FIX 2: store invoice items ONCE (no duplicates)
        names = request.form.getlist("item_name[]")
        amounts = request.form.getlist("item_amount[]")

        for name, amt in zip(names, amounts):
            if not name.strip():
                continue

            item = InvoiceItem(
                invoice_id=invoice.id,
                item_name=name.strip(),
                amount=float(amt or 0)
            )
            db.session.add(item)

        db.session.commit()

        # optional initial payment
        paid_now = float(request.form.get("paid_now", 0) or 0)
        if paid_now > 0:
            payment = Payment(
                invoice_id=invoice.id,
                amount=paid_now,
                paid_at=datetime.now()
            )
            db.session.add(payment)

            # update invoice status
            if abs(paid_now - invoice.total_amount) < 0.001:
                invoice.status = "Paid"
            else:
                invoice.status = "Partial"

            db.session.commit()

        flash("Invoice created successfully.", "success")
        return redirect(url_for("billing_bp.billing"))

    return render_template(
        "billing/create_invoice.html",
        patients=patients,
        new_invoice_number=new_invoice_number
    )

@billing_bp.route("/view/<int:id>", methods=["GET"])
def view_invoice(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    inv = get_secure_invoice(id)

    paid = sum(p.amount for p in inv.payments)
    balance = inv.total_amount - paid
    return render_template("billing/view_invoice.html", inv=inv, paid=paid, balance=balance)

@billing_bp.route("/download/<int:id>", methods=["GET"])
def download_invoice(id):
    # Renders an invoice HTML (print-ready). If you want PDF, see notes below.
    # inv = Invoice.query.get_or_404(id)
    # paid = sum(p.amount for p in inv.payments)
    # balance = inv.total_amount - paid
    # user = User.query.filter_by(id=session["user_id"]).first()
    # rendered = render_template(
    #     "invoice_pdf.html",
    #     inv=inv,
    #     paid=paid,
    #     balance=balance,
    #     clinic_name=user.clinic_name,
    #     clinic_phone=user.clinic_phone,
    #     clinic_address=user.clinic_address
    # )
    return " commming soon"





@billing_bp.route("/delete/<int:id>", methods=["GET"])
def delete_invoice(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))
    inv = get_secure_invoice(id)

    # cascade delete items & payments if you prefer; removing rows explicitly:
    InvoiceItem.query.filter_by(invoice_id=inv.id).delete()
    Payment.query.filter_by(invoice_id=inv.id).delete()
    db.session.delete(inv)
    db.session.commit()
    flash("Invoice deleted.", "warning")
    return redirect(url_for("billing_bp.billing"))

@billing_bp.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_invoice(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))
    inv = get_secure_invoice(id)
    patients = Patient.query.filter_by(
        user_id=session["user_id"]
    ).order_by(Patient.name).all()


    if request.method == "POST":
        inv.patient_id = int(request.form["patient_id"])
        inv.description = request.form.get("description", "")
        inv.total_amount = float(request.form.get("total_amount", 0) or 0)
        db.session.commit()

        # replace items (simple approach)
        InvoiceItem.query.filter_by(invoice_id=inv.id).delete()
        names = request.form.getlist("item_name[]")
        amounts = request.form.getlist("item_amount[]")
        for name, amt in zip(names, amounts):
            if not name.strip(): continue
            db.session.add(InvoiceItem(invoice_id=inv.id, item_name=name.strip(), amount=float(amt or 0)))
        db.session.commit()

        flash("Invoice updated.", "success")
        return redirect(url_for("billing_bp.view_invoice", id=inv.id))

    return render_template("billing/edit_invoice.html", inv=inv, patients=patients)

@billing_bp.route("/add_payment/<int:id>", methods=["POST"])
def add_payment(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))
    inv = get_secure_invoice(id)

    amt = float(request.form.get("amount", 0) or 0)
    method = request.form.get("method", "Cash")
    if amt <= 0:
        flash("Enter valid amount.", "danger")
        return redirect(url_for("billing_bp.view_invoice", id=id))
    payment = Payment(invoice_id=inv.id, amount=amt, method=method, paid_at=datetime.now().strftime("%Y-%m-%d"))
    db.session.add(payment)
    db.session.commit()

    paid = sum(p.amount for p in inv.payments)
    if abs(paid - inv.total_amount) < 0.001:
        inv.status = "Paid"
    elif paid > 0:
        inv.status = "Partial"
    else:
        inv.status = "Unpaid"
    db.session.commit()
    flash("Payment recorded.", "success")
    return redirect(url_for("billing_bp.view_invoice", id=id))
