from flask import Blueprint, request, redirect, url_for, flash, session
import razorpay
from clinic.extensions import db
from clinic.models import Clinic, Subscription
from datetime import datetime, timedelta
import os
try:
    import razorpay
except ImportError:
    razorpay = None

payments_bp = Blueprint("payments_bp", __name__, url_prefix="/payments")

def get_razorpay_client():
    if razorpay is None:
        raise RuntimeError("Razorpay not installed")

    key = os.environ.get("RAZORPAY_KEY")
    secret = os.environ.get("RAZORPAY_SECRET")

    if not key or not secret:
        raise RuntimeError("Razorpay keys not configured")

    return razorpay.Client(auth=(key, secret))



@payments_bp.route("/create/<plan>", methods=["POST"])
def create_payment(plan):
    clinic = Clinic.query.get_or_404(session["clinic_id"])

    prices = {
        "basic": 199,
        "pro": 499,
        "clinic+": 999
    }

    amount = prices.get(plan)
    if not amount:
        flash("Invalid plan", "danger")
        return redirect(url_for("settings_bp.settings"))
    
    client = get_razorpay_client()
    order = client.order.create({
        "amount": amount * 100,
        "currency": "INR",
        "receipt": f"clinic_{clinic.id}"
    })

    sub = Subscription(
        clinic_id=clinic.id,
        plan=plan,
        amount=amount,
        status="pending",
        provider="razorpay",
        provider_order_id=order["id"]
    )

    db.session.add(sub)
    db.session.commit()

    return {
        "order_id": order["id"],
        "amount": amount * 100,
        "key": os.environ.get("RAZORPAY_KEY")
    }

@payments_bp.route("/verify", methods=["POST"])
def verify_payment():
    data = request.json

    client = get_razorpay_client()
    client.utility.verify_payment_signature({
        "razorpay_order_id": data["order_id"],
        "razorpay_payment_id": data["payment_id"],
        "razorpay_signature": data["signature"]
    })

    sub = Subscription.query.filter_by(
        provider_order_id=data["order_id"]
    ).first_or_404()

    now = datetime.utcnow()

    sub.status = "active"
    sub.started_at = now
    sub.ends_at = now + timedelta(days=30)

    clinic = Clinic.query.get(sub.clinic_id)
    clinic.plan = sub.plan
    clinic.subscription_status = "active"
    clinic.subscription_ends_at = sub.ends_at

    db.session.commit()
    return {"status": "success"}
