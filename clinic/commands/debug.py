import click
from flask.cli import with_appcontext
from clinic.extensions import db
from clinic.models import Patient, User

@click.command("clinic-debug")
@with_appcontext
def clinic_debug():
    print("\n--- PATIENT COUNT PER CLINIC ---")

    rows = (
        db.session.query(
            Patient.clinic_owner_id,
            db.func.count(Patient.id)
        )
        .group_by(Patient.clinic_owner_id)
        .all()
    )

    for owner_id, count in rows:
        doctor = User.query.get(owner_id)
        name = doctor.fullname if doctor else "UNKNOWN"
        print(f"Doctor {owner_id} ({name}) → {count} patients")

    print("\n--- ORPHAN PATIENTS ---")
    orphans = (
        Patient.query
        .outerjoin(User, Patient.clinic_owner_id == User.id)
        .filter(User.id == None)
        .all()
    )

    if not orphans:
        print("No orphan patients found ✅")
    else:
        for p in orphans:
            print(f"Patient ID {p.id} | {p.name} | clinic_owner_id={p.clinic_owner_id}")
