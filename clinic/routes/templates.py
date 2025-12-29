from flask import Blueprint, render_template, request, jsonify
from ..extensions import db
from ..models import PrescriptionTemplate, PrescriptionTemplateItem
from clinic.routes.auth import login_required, role_required
from clinic.utils import get_current_clinic_owner_id
from clinic.extensions import csrf

templates_bp = Blueprint("templates_bp", __name__)

# -----------------------------------------------
# SAVE TEMPLATE
# -----------------------------------------------
@templates_bp.route("/templates/save", methods=["POST"])
@login_required
@role_required("doctor")
@csrf.exempt
def save_template():

    data = request.get_json(silent=True)
    if not data or not data.get("name"):
        return jsonify({"error": "Invalid data"}), 400

    clinic_owner_id = get_current_clinic_owner_id()

    template = PrescriptionTemplate(
        clinic_owner_id=clinic_owner_id,
        name=data["name"],
        symptoms=data.get("symptoms", ""),
        diagnosis=data.get("diagnosis", "")
    )

    db.session.add(template)
    db.session.flush()  # get template.id

    for item in data.get("items", []):
        if not item.get("medicine"):
            continue

        db.session.add(
            PrescriptionTemplateItem(
                template_id=template.id,
                medicine_name=item["medicine"],
                dose=item.get("dose"),
                duration_days=item.get("days"),
                instructions=item.get("notes")
            )
        )

    db.session.commit()
    return jsonify({"status": "saved"})


# -----------------------------------------------
# SEARCH TEMPLATES
# -----------------------------------------------
@templates_bp.route("/templates/search")
@login_required
@role_required("doctor")
def search_templates():

    q = request.args.get("q", "").lower()
    clinic_owner_id = get_current_clinic_owner_id()

    templates = PrescriptionTemplate.query.filter(
        PrescriptionTemplate.clinic_owner_id == clinic_owner_id,
        PrescriptionTemplate.symptoms.ilike(f"%{q}%")
    ).all()

    return jsonify([
        {"id": t.id, "name": t.name}
        for t in templates
    ])


# -----------------------------------------------
# GET TEMPLATE (APPLY)
# -----------------------------------------------
@templates_bp.route("/templates/<int:id>")
@login_required
@role_required("doctor")
def get_template(id):

    clinic_owner_id = get_current_clinic_owner_id()

    template = PrescriptionTemplate.query.filter_by(
        id=id,
        clinic_owner_id=clinic_owner_id
    ).first_or_404()

    return jsonify({
        "items": [
            {
                "medicine": i.medicine_name,
                "dose": i.dose,
                "days": i.duration_days,
                "notes": i.instructions
            }
            for i in template.items
        ]
    })


# -----------------------------------------------
# TEMPLATE MANAGER SCREEN
# -----------------------------------------------
@templates_bp.route("/templates")
@login_required
@role_required("doctor")
def template_manager():

    clinic_owner_id = get_current_clinic_owner_id()

    templates = PrescriptionTemplate.query.filter_by(
        clinic_owner_id=clinic_owner_id
    ).order_by(PrescriptionTemplate.created_at.desc()).all()

    return render_template(
        "appointments/templates.html",
        templates=templates
    )


# -----------------------------------------------
# DELETE TEMPLATE
# -----------------------------------------------
@templates_bp.route("/templates/delete/<int:id>", methods=["POST"])
@login_required
@role_required("doctor")
@csrf.exempt
def delete_template(id):

    clinic_owner_id = get_current_clinic_owner_id()

    template = PrescriptionTemplate.query.filter_by(
        id=id,
        clinic_owner_id=clinic_owner_id
    ).first_or_404()

    db.session.delete(template)
    db.session.commit()

    return jsonify({"status": "deleted"})
