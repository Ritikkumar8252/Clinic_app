let saveTimeout = null;

// Called when typing in any field
function autoSave() {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(sendSaveRequest, 800);
}

// Send consultation data to backend
function sendSaveRequest() {

    if (!window.autosaveUrl) {
        console.error("Autosave URL not set");
        return;
    }

    const payload = {};

    const symptoms = document.getElementById("symptoms-hidden");
    if (symptoms && symptoms.value.trim() !== "") {
        payload.symptoms = symptoms.value;
    }

    const diagnosis = document.getElementById("diagnosis-hidden");
    if (diagnosis && diagnosis.value.trim() !== "") {
        payload.diagnosis = diagnosis.value;
    }

    const advice = document.getElementById("advice-hidden");
    if (advice && advice.value.trim() !== "") {
        payload.advice = advice.value;
    }

    const fields = ["bp", "pulse", "spo2", "temperature", "weight", "follow_up_date"];
    fields.forEach(id => {
        const el = document.getElementById(id);
        if (el && el.value.trim() !== "") {
            payload[id] = el.value;
        }
    });

    // do not send empty payload
    if (Object.keys(payload).length === 0) {
        return;
    }

    fetch(window.autosaveUrl, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    })
    .then(() => showToast())
    .catch(err => console.error("Autosave failed:", err));
}

// Show "Saved" toast
function showToast() {
    const toast = document.getElementById("saveToast");
    toast.style.opacity = "1";
    setTimeout(() => toast.style.opacity = "0", 1200);
}
