
/* ======================================
   BUILD PRESCRIPTION ITEMS (SOURCE OF TRUTH)
====================================== */
function collectPrescriptionItems() {
    const rows = document.querySelectorAll("#medBody tr");
    const items = [];

    rows.forEach(row => {
        const inputs = row.querySelectorAll("input");
        if (inputs.length < 4) return;

        const med = inputs[0].value.trim();
        const dose = inputs[1].value.trim();
        const days = inputs[2].value.trim();
        const notes = inputs[3].value.trim();

        if (!med) return;

        items.push({
            medicine: med,
            dose: dose,
            days: days,
            notes: notes
        });
    });

    return items;
}

/* ======================================
   BUILD FINAL SNAPSHOT TEXT (PDF / LEGAL)
====================================== */
function buildPrescriptionText(items) {
    let lines = [];

    items.forEach(item => {
        let line = `${item.medicine} | ${item.dose} | ${item.days} days`;
        if (item.notes) line += ` | ${item.notes}`;
        lines.push(line);
    });

    return lines.join("\n");
}

/* ======================================
   MEDICINE ROW HANDLING
====================================== */
function addRow() {
    const body = document.getElementById("medBody");
    const tr = document.createElement("tr");

    tr.innerHTML = `
        <td><input></td>
        <td><input></td>
        <td><input></td>
        <td><input></td>
        <td><button class="del-btn" onclick="removeRow(this)">x</button></td>
    `;

    body.appendChild(tr);
}

function removeRow(btn) {
    btn.closest("tr").remove();
}

document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("addRowBtn");
    if (btn) btn.onclick = addRow;
});

/* ======================================
   TEMPLATES
====================================== */
document.addEventListener("click", e => {
    const box = document.getElementById("templateBox");
    if (!box.contains(e.target) && !e.target.closest(".btn-grey")) {
        box.style.display = "none";
    }
});


/* ======================================
   FINALIZE + SAVE + DOWNLOAD (FIXED FLOW)
====================================== */
async function finalizeAndPrint(e) {
    e.preventDefault();

    const items = collectPrescriptionItems();

    if (items.length === 0) {
        alert("Please add at least one medicine");
        return false;
    }

    // 1️⃣ SAVE MEDICINES (DB SOURCE OF TRUTH)
    const saveRes = await fetch(`/save_prescription/${window.apptId}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ items })
    });

    if (!saveRes.ok) {
        alert("Failed to save medicines");
        return false;
    }

    // 2️⃣ BUILD FINAL SNAPSHOT TEXT
    const finalText = buildPrescriptionText(items);
    document.getElementById("finalPrescription").value = finalText;

    // 3️⃣ FINALIZE (LOCKS PRESCRIPTION)
    const form = e.target;
    const finalizeRes = await fetch(form.action, {
        method: "POST",
        body: new FormData(form)
    });

    if (!finalizeRes.ok) {
        alert("Failed to finalize prescription");
        return false;
    }

    // 4️⃣ DOWNLOAD PDF (GUARANTEED)
    window.open(`/prescription/${window.apptId}`, "_blank");
    return false;
}
// templates
function openTemplateBox() {
    const q = document.getElementById("symptoms-hidden").value;
    fetch(`/templates/search?q=${q}`)
        .then(r => r.json())
        .then(data => {
            const box = document.getElementById("templateBox");
            box.innerHTML = "";
            data.forEach(t => {
                box.innerHTML += `
                    <div onclick="applyTemplateFromServer(${t.id})">
                        ${t.name}
                    </div>`;
            });
            box.style.display = "block";
        });
}
function applyTemplateFromServer(id) {
    fetch(`/templates/${id}`)
        .then(r => r.json())
        .then(data => {
            const body = document.getElementById("medBody");
            body.innerHTML = "";

            data.items.forEach(item => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><input value="${item.medicine}"></td>
                    <td><input value="${item.dose || ""}"></td>
                    <td><input value="${item.days || ""}"></td>
                    <td><input value="${item.notes || ""}"></td>
                    <td><button onclick="removeRow(this)">x</button></td>
                `;
                body.appendChild(tr);
            });
        });
}
function saveAsTemplate() {

    if (window.prescriptionLocked === "true") {
        alert("Finalize ke baad template save nahi hota");
        return;
    }

    const items = collectPrescriptionItems();
    if (items.length === 0) {
        alert("Template ke liye kam se kam 1 medicine zaroori hai");
        return;
    }

    const symptoms = document.getElementById("symptoms-hidden").value;
    if (!symptoms.trim()) {
        alert("Symptoms likhe bina template save nahi hoga");
        return;
    }

    const name = prompt("Template name?");
    if (!name) return;

    fetch("/templates/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name,
            symptoms,
            diagnosis: document.getElementById("diagnosis-hidden").value,
            items
        })
    });
}


