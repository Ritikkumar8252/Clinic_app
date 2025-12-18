/* ======================================
   BUILD PRESCRIPTION TEXT FOR DB + PDF
====================================== */
function buildPrescriptionText() {
    let rows = document.querySelectorAll("#medBody tr");
    let lines = [];

    rows.forEach(row => {
        let inputs = row.querySelectorAll("input");
        if (inputs.length < 4) return;

        let med = inputs[0].value.trim();
        let dose = inputs[1].value.trim();
        let days = inputs[2].value.trim();
        let notes = inputs[3].value.trim();

        if (!med) return;

        let line = `• ${med} | ${dose} | ${days} days`;
        if (notes) line += ` | ${notes}`;

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
        <td><input oninput="autoSave()"></td>
        <td><input oninput="autoSave()"></td>
        <td><input oninput="autoSave()"></td>
        <td><input oninput="autoSave()"></td>
        <td><button class="del-btn" onclick="removeRow(this)">x</button></td>
    `;

    body.appendChild(tr);
}

function removeRow(btn) {
    btn.closest("tr").remove();
    autoSave();
}

document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("addRowBtn");
    if (btn) btn.onclick = addRow;
});

/* ======================================
   TEMPLATES
====================================== */
function toggleTemplates() {
    document.getElementById("templateBox").classList.toggle("show");
}

const templates = {
    "Fever Standard": [
        { med: "Paracetamol 650mg", dose: "1-0-1", days: "5", notes: "After food" }
    ],
    "Viral Infection": [
        { med: "Dolo 650", dose: "1-1-1", days: "3", notes: "" }
    ]
};

function applyTemplate(name) {
    const body = document.getElementById("medBody");
    body.innerHTML = "";

    templates[name].forEach(item => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><input value="${item.med}" oninput="autoSave()"></td>
            <td><input value="${item.dose}" oninput="autoSave()"></td>
            <td><input value="${item.days}" oninput="autoSave()"></td>
            <td><input value="${item.notes}" oninput="autoSave()"></td>
            <td><button class="del-btn" onclick="removeRow(this)">x</button></td>
        `;
        body.appendChild(tr);
    });

    addRow();
    autoSave();
    toggleTemplates();
}
/* ======================================
    FINALIZE
====================================== */
function prepareFinalize() {
    let text = buildPrescriptionText();

    if (!text.trim()) {
        alert("Prescription is empty. Add at least one medicine.");
        return false;
    }

    document.getElementById("finalPrescription").value = text;
    return true;
}

function finalizeAndPrint(e) {
    e.preventDefault();

    let text = buildPrescriptionText();

    if (!text.trim()) {
        alert("Please add at least one medicine");
        return false;
    }

    document.getElementById("finalPrescription").value = text;

    const form = e.target;

    fetch(form.action, {
        method: "POST",
        body: new FormData(form)
    })
    .then(res => {
        if (!res.ok) throw new Error("Finalize failed");

        // 👇 OPEN PDF IN NEW TAB (GUARANTEED)
        window.open(
            `/prescription/${window.apptId}`,
            "_blank"
        );
    })
    .catch(() => {
        alert("Failed to finalize prescription");
    });

    return false;
}
