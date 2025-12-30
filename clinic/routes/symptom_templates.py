from flask import Blueprint, request, jsonify
from clinic.extensions import db
from clinic.models import SymptomTemplate
from clinic.routes.auth import login_required, role_required
from clinic.utils import get_current_clinic_owner_id
from clinic.extensions import csrf

symptom_templates_bp = Blueprint(
    "symptom_templates_bp",
    __name__,
    url_prefix="/symptom-templates"
)

# -----------------------------
# SAVE TEMPLATE
# -----------------------------
@symptom_templates_bp.route("/save", methods=["POST"])
@login_required
@role_required("doctor")
@csrf.exempt
def save_symptom_template():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    name = data.get("name", "").strip()
    content = data.get("content", "").strip()

    if not name or not content:
        return jsonify({"error": "Name and content required"}), 400

    clinic_owner_id = get_current_clinic_owner_id()

    exists = SymptomTemplate.query.filter_by(
        clinic_owner_id=clinic_owner_id,
        name=name
    ).first()

    if exists:
        return jsonify({"error": "Template already exists"}), 409

    template = SymptomTemplate(
        clinic_owner_id=clinic_owner_id,
        name=name,
        content=content
    )

    db.session.add(template)
    db.session.commit()

    return jsonify({"status": "saved"}), 201

# -----------------------------
# SEARCH / LIST TEMPLATES
# -----------------------------
@symptom_templates_bp.route("/search")
@login_required
@role_required("doctor")
def search_symptom_templates():
    q = request.args.get("q", "").strip()
    clinic_owner_id = get_current_clinic_owner_id()

    query = SymptomTemplate.query.filter_by(
        clinic_owner_id=clinic_owner_id
    )

    if q:
        query = query.filter(
            SymptomTemplate.name.ilike(f"%{q}%") |
            SymptomTemplate.content.ilike(f"%{q}%")
        )

    results = query.order_by(
        SymptomTemplate.created_at.desc()
    ).limit(10).all()

    return jsonify([
        {
            "id": t.id,
            "name": t.name,
            "content": t.content
        }
        for t in results
    ])

@symptom_templates_bp.route("/<int:id>", methods=["PUT"])
@login_required
@role_required("doctor")
@csrf.exempt
def update_symptom_template(id):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    clinic_owner_id = get_current_clinic_owner_id()

    template = SymptomTemplate.query.filter_by(
        id=id,
        clinic_owner_id=clinic_owner_id
    ).first_or_404()

    name = data.get("name", "").strip()
    content = data.get("content", "").strip()

    if not name or not content:
        return jsonify({"error": "Name and content required"}), 400

    template.name = name
    template.content = content

    db.session.commit()

    return jsonify({"status": "updated"})

@symptom_templates_bp.route("/<int:id>", methods=["DELETE"])
@login_required
@role_required("doctor")
@csrf.exempt
def delete_symptom_template(id):
    clinic_owner_id = get_current_clinic_owner_id()

    template = SymptomTemplate.query.filter_by(
        id=id,
        clinic_owner_id=clinic_owner_id
    ).first_or_404()

    db.session.delete(template)
    db.session.commit()

    return jsonify({"status": "deleted"})
