let saveTimeout = null;

/* ===============================
   UI STATUS
================================ */
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

/* ===============================
   AUTOSAVE TRIGGER
================================ */
function autoSave() {
    showSaving();

    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(sendSaveRequest, 800);
}

/* ===============================
   BUILD & SEND PAYLOAD
================================ */
function sendSaveRequest() {
    // 🔒 Do nothing if finalized
    if (window.prescriptionLocked === "true") return;
    if (!window.autosaveUrl) return;

    const payload = {};

    /* ---------- TEXT FIELDS ---------- */
    ["symptoms", "diagnosis", "advice", "lab_tests"].forEach(id => {
        const el = document.getElementById(id);
        if (el && el.value.trim()) {
            payload[id] = el.value.trim();
        }
    });

    /* ---------- FOLLOW UP DATE ---------- */
    const followUp = document.getElementById("follow_up_date");
    if (followUp && followUp.value) {
        payload["follow_up_date"] = followUp.value;
    }

    /* ---------- DYNAMIC VITALS ---------- */
    document.querySelectorAll(".vital-row input").forEach(el => {
        if (!el.id) return;
        if (!el.value.trim()) return;

        payload[el.id] = el.value.trim();
    });

    // nothing to save
    if (Object.keys(payload).length === 0) return;

    /* ---------- SEND ---------- */
    fetch(window.autosaveUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    })
    .then(() => {
        showSaved();
        if (typeof showToast === "function") {
            showToast();
        }
    })
    .catch(() => {
        // silent fail (doctor should never panic)
    });
}
