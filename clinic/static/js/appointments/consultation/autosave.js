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

    const payload = {
        symptoms: document.getElementById("symptoms-hidden").value || "",
        diagnosis: document.getElementById("diagnosis-hidden").value || "",
        advice: document.getElementById("advice-hidden").value || "",

        bp: document.getElementById("bp")?.value || "",
        pulse: document.getElementById("pulse")?.value || "",
        spo2: document.getElementById("spo2")?.value || "",
        temperature: document.getElementById("temperature")?.value || "",
        weight: document.getElementById("weight")?.value || "",
        follow_up_date: document.getElementById("follow_up_date")?.value || ""
    };

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
