let saveTimeout = null;

function autoSave() {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(sendSaveRequest, 800);
}

function sendSaveRequest() {

    if (!window.autosaveUrl) return;

    const payload = {};

    // Prescription text
    if (window.buildPrescriptionText) {
        const pres = buildPrescriptionText();
        if (pres.trim()) payload.prescription = pres;
    }

    // Hidden textareas
    ["symptoms", "diagnosis", "advice"].forEach(field => {
        const el = document.getElementById(field + "-hidden");
        if (el && el.value.trim()) {
            payload[field] = el.value.trim();
        }
    });

    // Vitals
    ["bp", "pulse", "spo2", "temperature", "weight", "follow_up_date"]
        .forEach(id => {
            const el = document.getElementById(id);
            if (el && el.value.trim()) {
                payload[id] = el.value.trim();
            }
        });

    // 🚫 Prevent empty autosave
    if (Object.keys(payload).length === 0) return;

    fetch(window.autosaveUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    })
    .then(() => showToast())
    .catch(() => {});
}

function showToast() {
    const toast = document.getElementById("saveToast");
    if (!toast) return;
    toast.style.opacity = "1";
    setTimeout(() => toast.style.opacity = "0", 1200);
}
