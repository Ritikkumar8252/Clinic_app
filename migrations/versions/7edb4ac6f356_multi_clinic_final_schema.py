"""multi clinic final schema

Revision ID: 7edb4ac6f356
Revises: b745eee5f961
"""

from alembic import op
import sqlalchemy as sa

revision = "7edb4ac6f356"
down_revision = "b745eee5f961"
branch_labels = None
depends_on = None


def upgrade():

    # -------------------------------------------------
    # 1. CLINIC
    # -------------------------------------------------
    op.create_table(
        "clinic",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(50)),
        sa.Column("address", sa.String(300)),
        sa.Column("owner_id", sa.Integer(), unique=True),
        sa.Column("created_at", sa.DateTime()),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
    )

    # -------------------------------------------------
    # 2. USER → add clinic_id FIRST
    # -------------------------------------------------
    with op.batch_alter_table("user") as batch:
        batch.add_column(sa.Column("clinic_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(None, "clinic", ["clinic_id"], ["id"])

    # -------------------------------------------------
    # 3. CREATE CLINIC FOR EXISTING DOCTORS
    # -------------------------------------------------
    op.execute("""
        INSERT INTO clinic (id, name, created_at)
        SELECT u.id, COALESCE(u.clinic_name, 'Clinic ' || u.id), NOW()
        FROM "user" u
        WHERE u.role = 'doctor'
        AND NOT EXISTS (SELECT 1 FROM clinic c WHERE c.id = u.id)
    """)

    op.execute("""
        UPDATE "user"
        SET clinic_id = id
        WHERE role = 'doctor'
    """)

    # -------------------------------------------------
    # 4. PATIENT
    # -------------------------------------------------
    with op.batch_alter_table("patient") as batch:
        batch.add_column(sa.Column("clinic_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(None, "clinic", ["clinic_id"], ["id"])
        batch.create_index("ix_patient_clinic_id", ["clinic_id"])

    op.execute("""
        UPDATE patient
        SET clinic_id = clinic_id
    """)

    with op.batch_alter_table("patient") as batch:
        batch.alter_column("clinic_id", nullable=False)
        batch.drop_constraint("patient_clinic_id_fkey", type_="foreignkey")
        batch.drop_column("clinic_id")
        batch.create_unique_constraint(None, ["clinic_id", "patient_no"])

    # -------------------------------------------------
    # 5. APPOINTMENT
    # -------------------------------------------------
    with op.batch_alter_table("appointment") as batch:
        batch.add_column(sa.Column("clinic_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(None, "clinic", ["clinic_id"], ["id"])
        batch.create_index("ix_appointment_clinic_id", ["clinic_id"])

    op.execute("""
        UPDATE appointment a
        SET clinic_id = p.clinic_id
        FROM patient p
        WHERE a.patient_id = p.id
    """)

    with op.batch_alter_table("appointment") as batch:
        batch.alter_column("clinic_id", nullable=False)

    # -------------------------------------------------
    # 6. MEDICAL RECORD
    # -------------------------------------------------
    with op.batch_alter_table("medical_record") as batch:
        batch.add_column(sa.Column("clinic_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(None, "clinic", ["clinic_id"], ["id"])
        batch.create_index("ix_medical_record_clinic_id", ["clinic_id"])

    op.execute("""
        UPDATE medical_record m
        SET clinic_id = p.clinic_id
        FROM patient p
        WHERE m.patient_id = p.id
    """)

    with op.batch_alter_table("medical_record") as batch:
        batch.alter_column("clinic_id", nullable=False)

    # -------------------------------------------------
    # 7. INVOICE
    # -------------------------------------------------
    with op.batch_alter_table("invoice") as batch:
        batch.add_column(sa.Column("clinic_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(None, "clinic", ["clinic_id"], ["id"])
        batch.create_index("ix_invoice_clinic_id", ["clinic_id"])

    op.execute("""
        UPDATE invoice i
        SET clinic_id = p.clinic_id
        FROM patient p
        WHERE i.patient_id = p.id
    """)

    with op.batch_alter_table("invoice") as batch:
        batch.alter_column("clinic_id", nullable=False)

    # -------------------------------------------------
    # 8. INVOICE SEQUENCE (FIXED)
    # -------------------------------------------------
    with op.batch_alter_table("invoice_sequence") as batch:
        batch.add_column(sa.Column("clinic_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(None, "clinic", ["clinic_id"], ["id"])

    op.execute("""
        UPDATE invoice_sequence s
        SET clinic_id = u.clinic_id
        FROM "user" u
        WHERE s.clinic_id = u.id
    """)

    with op.batch_alter_table("invoice_sequence") as batch:
        batch.alter_column("clinic_id", nullable=False)
        batch.drop_constraint("invoice_sequence_clinic_id_fkey", type_="foreignkey")
        batch.drop_column("clinic_id")
        batch.create_unique_constraint(None, ["clinic_id"])

   # -------------------------------------------------
    # 9. AUDIT LOG (FINAL FIX)
    # -------------------------------------------------
    with op.batch_alter_table("audit_log") as batch:
        batch.add_column(sa.Column("clinic_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(None, "clinic", ["clinic_id"], ["id"])
        batch.create_index("ix_audit_log_clinic_id", ["clinic_id"])

    # 1️⃣ Populate from user (normal case)
    op.execute("""
        UPDATE audit_log a
        SET clinic_id = u.clinic_id
        FROM "user" u
        WHERE a.user_id = u.id
    """)

    # 2️⃣ Fallback for system / orphan logs
    # Assign them to ANY existing clinic (first one)
    op.execute("""
        UPDATE audit_log
        SET clinic_id = (
            SELECT id FROM clinic ORDER BY id LIMIT 1
        )
        WHERE clinic_id IS NULL
    """)

    with op.batch_alter_table("audit_log") as batch:
        batch.alter_column("clinic_id", nullable=False)
        batch.drop_constraint("audit_log_clinic_id_fkey", type_="foreignkey")
        batch.drop_column("clinic_id")

    # -------------------------------------------------
    # 10. PRESCRIPTION TEMPLATE
    # -------------------------------------------------
    with op.batch_alter_table("prescription_template") as batch:
        batch.add_column(sa.Column("clinic_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(None, "clinic", ["clinic_id"], ["id"])
        batch.create_index("ix_prescription_template_clinic_id", ["clinic_id"])

    op.execute("""
        UPDATE prescription_template
        SET clinic_id = clinic_id
    """)

    with op.batch_alter_table("prescription_template") as batch:
        batch.alter_column("clinic_id", nullable=False)
        batch.drop_constraint("prescription_template_clinic_id_fkey", type_="foreignkey")
        batch.drop_column("clinic_id")
        batch.create_unique_constraint(None, ["clinic_id", "name"])

    # -------------------------------------------------
    # 11. SYMPTOM TEMPLATE
    # -------------------------------------------------
    with op.batch_alter_table("symptom_template") as batch:
        batch.add_column(sa.Column("clinic_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(None, "clinic", ["clinic_id"], ["id"])

    op.execute("""
        UPDATE symptom_template
        SET clinic_id = clinic_id
    """)

    with op.batch_alter_table("symptom_template") as batch:
        batch.alter_column("clinic_id", nullable=False)
        batch.drop_constraint("symptom_template_clinic_id_fkey", type_="foreignkey")
        batch.drop_column("clinic_id")


def downgrade():
    raise RuntimeError("Downgrade not supported for multi-clinic migration")
