from clinic.extensions import db
from clinic.models import InvoiceSequence

def generate_invoice_number():
    seq = InvoiceSequence.query.with_for_update().first()

    if not seq:
        seq = InvoiceSequence(last_number=1)
        db.session.add(seq)
        db.session.flush()
        return f"INV-{seq.last_number:05d}"

    seq.last_number += 1
    db.session.flush()

    return f"INV-{seq.last_number:05d}"
