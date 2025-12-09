# billing.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_file
from clinic.extensions import db
from clinic.models import Patient, Invoice, InvoiceItem, Payment
from datetime import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

billing_bp = Blueprint("billing_bp", __name__, url_prefix="/billing")


def generate_invoice_number():
    last = Invoice.query.order_by(Invoice.id.desc()).first()
    if last and last.invoice_number:
        # try to parse numeric suffix, otherwise increment id
        try:
            # keep format INV-0001
            num = int(last.invoice_number.split("-")[-1])
            return f"INV-{num+1:04}"
        except Exception:
            return f"INV-{last.id + 1:04}"
    return "INV-0001"


@billing_bp.route("/", methods=["GET"])
def billing():
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    # filters
    q = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()

    invoices = Invoice.query.order_by(Invoice.created_at.desc())

    if q:
        # search by invoice number or patient name
        invoices = invoices.join(Patient).filter(
            (Invoice.invoice_number.ilike(f"%{q}%")) |
            (Patient.name.ilike(f"%{q}%"))
        )

    if status:
        invoices = invoices.filter(Invoice.status == status)

    invoices = invoices.all()

    # count overdue/unpaid
    due_count = Invoice.query.filter(Invoice.status != "Paid").count()

    return render_template("billing.html", invoices=invoices, due_count=due_count)


@billing_bp.route("/create_invoice", methods=["GET", "POST"])
def create_invoice():
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    patients = Patient.query.order_by(Patient.name).all()
    new_invoice_number = generate_invoice_number()

    if request.method == "POST":
        try:
            patient_id = int(request.form["patient_id"])
            invoice_number = request.form.get("invoice_number", new_invoice_number).strip()
            description = request.form.get("description", "").strip()
            total_amount = float(request.form.get("total_amount", 0) or 0)
            due_date = request.form.get("due_date", None)

            invoice = Invoice(
                patient_id=patient_id,
                invoice_number=invoice_number,
                description=description,
                total_amount=total_amount,
                due_date=due_date,
                status="Unpaid" if total_amount > 0 else "Paid",
                created_at=datetime.now().strftime("%Y-%m-%d")
            )
            db.session.add(invoice)
            db.session.flush()  # get invoice.id

            # invoice items
            item_names = request.form.getlist("item_name[]")
            item_amounts = request.form.getlist("item_amount[]")
            for name, amt in zip(item_names, item_amounts):
                if not name or name.strip() == "":
                    continue
                try:
                    a = float(amt or 0)
                except Exception:
                    a = 0.0
                item = InvoiceItem(invoice_id=invoice.id, item_name=name.strip(), amount=a)
                db.session.add(item)

            # recompute total from items (safer)
            db.session.flush()
            computed_total = sum(i.amount for i in invoice.items)
            invoice.total_amount = computed_total

            # optional immediate payment
            paid_now = float(request.form.get("paid_now", 0) or 0)
            if paid_now > 0:
                payment = Payment(invoice_id=invoice.id, amount=paid_now, method=request.form.get("payment_method", "Cash"), paid_at=datetime.now().strftime("%Y-%m-%d"))
                db.session.add(payment)
                # status update
                if abs(paid_now - invoice.total_amount) < 0.001:
                    invoice.status = "Paid"
                else:
                    invoice.status = "Partial"

            db.session.commit()
            flash("Invoice created successfully.", "success")
            return redirect(url_for("billing_bp.billing"))
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("create_invoice error")
            flash("Error creating invoice: " + str(e), "danger")
            return redirect(url_for("billing_bp.create_invoice"))

    return render_template("create_invoice.html", patients=patients, new_invoice_number=new_invoice_number)


@billing_bp.route("/view/<int:id>", methods=["GET"])
def view_invoice(id):
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    invoice = Invoice.query.get_or_404(id)
    # calculate paid and balance
    paid = sum(p.amount for p in invoice.payments) if invoice.payments else 0.0
    balance = invoice.total_amount - paid
    return render_template("view_invoice.html", invoice=invoice, paid=paid, balance=balance)


@billing_bp.route("/download/<int:id>", methods=["GET"])
def download_invoice(id):
    # simple PDF via reportlab — returns PDF as attachment
    invoice = Invoice.query.get_or_404(id)
    patient = invoice.patient
    paid = sum(p.amount for p in invoice.payments) if invoice.payments else 0.0
    balance = invoice.total_amount - paid

    buf = io.BytesIO()
    p = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # header
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, height - 60, current_app.config.get("CLINIC_NAME", "My Clinic"))
    p.setFont("Helvetica", 10)
    p.drawString(40, height - 80, current_app.config.get("CLINIC_ADDRESS", ""))

    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, height - 120, f"Invoice: {invoice.invoice_number}")
    p.setFont("Helvetica", 10)
    p.drawString(40, height - 135, f"Date: {invoice.created_at}")
    p.drawString(300, height - 135, f"Patient: {patient.name} | {patient.phone or ''}")

    # items
    y = height - 170
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y, "Item")
    p.drawString(350, y, "Amount (₹)")
    p.setFont("Helvetica", 10)
    y -= 18
    for it in invoice.items:
        p.drawString(40, y, it.item_name)
        p.drawRightString(460, y, f"₹ {it.amount:.2f}")
        y -= 16
        if y < 80:
            p.showPage()
            y = height - 60

    # totals
    y -= 6
    p.setFont("Helvetica-Bold", 11)
    p.drawRightString(460, y, f"Total: ₹ {invoice.total_amount:.2f}")
    y -= 18
    p.setFont("Helvetica", 10)
    p.drawRightString(460, y, f"Paid: ₹ {paid:.2f}")
    y -= 16
    p.drawRightString(460, y, f"Balance: ₹ {balance:.2f}")

    p.showPage()
    p.save()
    buf.seek(0)

    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=f"invoice-{invoice.invoice_number}.pdf")


@billing_bp.route("/delete/<int:id>", methods=["GET"])
def delete_invoice(id):
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    inv = Invoice.query.get_or_404(id)
    try:
        db.session.delete(inv)
        db.session.commit()
        flash("Invoice deleted", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting invoice: " + str(e), "danger")

    return redirect(url_for("billing_bp.billing"))
