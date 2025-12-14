let saveTimeout = null;

/* ===============================
   AUTOSAVE TRIGGER
================================ */
function autoSave() {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(sendSaveRequest, 800);
}

/* ===============================
   SEND DATA TO BACKEND
================================ */
function sendSaveRequest() {

    if (!window.autosaveUrl) {
        console.error("Autosave URL not set");
        return;
    }

    const payload = {};

    // Prescription (from prescription.js)
    if (window.buildPrescriptionText) {
        const pres = buildPrescriptionText();
        if (pres) payload.prescription = pres;
    }

    // Hidden fields
    ["symptoms", "diagnosis", "advice"].forEach(field => {
        const el = document.getElementById(field + "-hidden");
        if (el && el.value.trim()) {
            payload[field] = el.value;
        }
    });

    // Vitals
    ["bp", "pulse", "spo2", "temperature", "weight", "follow_up_date"]
        .forEach(id => {
            const el = document.getElementById(id);
            if (el && el.value.trim()) payload[id] = el.value;
        });

    if (Object.keys(payload).length === 0) return;

    fetch(window.autosaveUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
    .then(() => showToast())
    .catch(err => console.error("Autosave failed:", err));
}

/* ===============================
   SAVE TOAST
================================ */
function showToast() {
    const toast = document.getElementById("saveToast");
    if (!toast) return;
    toast.style.opacity = "1";
    setTimeout(() => toast.style.opacity = "0", 1200);
}
