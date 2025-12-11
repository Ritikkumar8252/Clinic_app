function addRow() {
    let body = document.getElementById("medBody");
    let tr = document.createElement("tr");
    tr.innerHTML = `
        <td><input name="medicine[]"></td>
        <td><input name="dose[]"></td>
        <td><input name="days[]"></td>
        <td><input name="notes[]"></td>
        <td><button class="del-btn" onclick="removeRow(this)">x</button></td>
    `;
    body.appendChild(tr);
}

function removeRow(btn) {
    btn.parentNode.parentNode.remove();
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("addRowBtn").onclick = addRow;
});

function toggleTemplates() {
    document.getElementById("templateBox").classList.toggle("show");
}

const templates = {
    "Fever Standard": [
        {med:"Paracetamol", dose:"1-0-1", days:"3", notes:"After food"}
    ],
    "Viral Infection": [
        {med:"Dolo 650", dose:"1-1-1", days:"3", notes:""}
    ]
};

function applyTemplate(name) {
    let body = document.getElementById("medBody");
    body.innerHTML = "";

    templates[name].forEach(item => {
        let tr = document.createElement("tr");
        tr.innerHTML = `
            <td><input name="medicine[]" value="${item.med}"></td>
            <td><input name="dose[]" value="${item.dose}"></td>
            <td><input name="days[]" value="${item.days}"></td>
            <td><input name="notes[]" value="${item.notes}"></td>
            <td><button class="del-btn" onclick="removeRow(this)">x</button></td>
        `;
        body.appendChild(tr);
    });

    addRow();
    toggleTemplates();
}
