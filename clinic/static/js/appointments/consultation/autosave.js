let saveTimeout = null;

function showSaving() {
    const el = document.getElementById("autosaveStatus");
    if (!el) return;
    el.textContent = "Saving…";
    el.classList.add("saving");
}

function showSaved() {
    const el = document.getElementById("autosaveStatus");
    if (!el) return;

    const now = new Date();
    const time = now.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit"
    });

    el.textContent = `Saved ✓ at ${time}`;
    el.classList.remove("saving");
}

function autoSave() {
    showSaving();

    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(sendSaveRequest, 800);
}

function sendSaveRequest() {
    if (window.prescriptionLocked === "true") return;
    if (!window.autosaveUrl) return;

    const payload = {};

    ["symptoms", "diagnosis", "advice", "lab_tests"].forEach(id => {
        const el = document.getElementById(id);
        if (el && el.value.trim()) {
            payload[id] = el.value.trim();
        }
    });

    ["bp", "pulse", "spo2", "temperature", "weight", "follow_up_date"]
        .forEach(id => {
            const el = document.getElementById(id);
            if (el && el.value.trim()) {
                payload[id] = el.value.trim();
            }
        });

    if (Object.keys(payload).length === 0) return;

    fetch(window.autosaveUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
    .then(() => {
        showSaved();
        showToast(); // keep your existing toast
    })
    .catch(() => {
        // silent fail (doctor should not panic)
    });
}
