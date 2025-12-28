let saveTimeout = null;

function autoSave() {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(sendSaveRequest, 800);
}

function sendSaveRequest() {

    if (!window.autosaveUrl) return;

    const payload = {};

    // Tags (hidden inputs)
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

    // ✅ LAB TESTS (OUTSIDE LOOP)
    const lab = document.getElementById("lab_tests");
    if (lab && lab.value.trim()) {
        payload.lab_tests = lab.value.trim();
    }

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
