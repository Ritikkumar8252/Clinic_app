
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

    // 1️⃣ SAVE MEDICINES (only if not finalized)
    const saveRes = await fetch(`/save_prescription/${window.apptId}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ items })
    });

    // 🔐 If already finalized → ignore silently
    if (saveRes.status === 403) {
        // already finalized, do not show error
    } else if (!saveRes.ok) {
        alert("Failed to save medicines");
        return false;
    }

    // 2️⃣ FINALIZE (backend locks prescription)
    const form = e.target;
    const finalizeRes = await fetch(form.action, {
        method: "POST",
        body: new FormData(form)
    });

    if (!finalizeRes.ok) {
        alert("Failed to finalize prescription");
        return false;
    }

    // 3️⃣ OPEN PDF
    window.location.href = `/prescription/${window.apptId}`;
    return false;
}

// templates
function openTemplateBox() {
    fetch(`/templates/search`)
        .then(r => r.json())
        .then(data => {
            const box = document.getElementById("templateBox");
            box.innerHTML = "";

            if (data.length === 0) {
                box.innerHTML = "<div class='template-item'>No templates</div>";
                box.style.display = "block";
                return;
            }

            data.forEach(t => {
                const div = document.createElement("div");
                div.className = "template-item";
                div.innerText = t.name;
                div.onclick = () => applyTemplateFromServer(t.id);
                box.appendChild(div);
            });

            box.style.display = "block";
        });
}

function applyTemplateFromServer(id) {
    fetch(`/templates/${id}`)
        .then(r => r.json())
        .then(data => {

            const body = document.getElementById("medBody");
            if (!body) return;

            // clear table
            body.innerHTML = "";

            data.items.forEach(item => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><input value="${item.medicine || ""}"></td>
                    <td><input value="${item.dose || ""}"></td>
                    <td><input value="${item.days || ""}"></td>
                    <td><input value="${item.notes || ""}"></td>
                    <td><button class="del-btn" onclick="removeRow(this)">x</button></td>
                `;
                body.appendChild(tr);
            });
        });
}

function saveAsTemplate() {

    if (window.prescriptionLocked === "true") {
    document.querySelectorAll(".btn-save, #addRowBtn, .del-btn")
        .forEach(el => el.disabled = true);
    }

    const items = collectPrescriptionItems();
    if (items.length === 0) {
        alert("Template ke liye kam se kam 1 medicine zaroori hai");
        return;
    }

    const symptoms = document.getElementById("symptoms").value;

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
            diagnosis: document.getElementById("diagnosis").value,

            items
        })
    });
}


