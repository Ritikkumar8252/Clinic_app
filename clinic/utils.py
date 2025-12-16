from clinic.models import Invoice, Patient

def generate_invoice_number(user_id):
    last_invoice = (
        Invoice.query
        .join(Patient)
        .filter(Patient.user_id == user_id)
        .order_by(Invoice.id.desc())
        .first()
    )

    if not last_invoice:
        return "INV-0001"

    last_no = int(last_invoice.invoice_number.split("-")[1])
    return f"INV-{last_no + 1:04}"
