PLANS = {
    "trial": {
        "patients_per_day": 20,
        "staff_limit": 0,
        "billing": False,
    },
    "basic": {
        "patients_per_day": 60,
        "staff_limit": 2,
        "billing": True,
    },
    "pro": {
        "patients_per_day": 150,
        "staff_limit": 5,
        "billing": True,
    },
    "clinic+": {
        "patients_per_day": None,  # unlimited
        "staff_limit": None,
        "billing": True,
    }
}
