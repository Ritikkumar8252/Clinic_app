document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.querySelector(".search-box");
    const tableBody = document.getElementById("patientTable");

    if (!searchInput || !tableBody) return;

    const rows = Array.from(tableBody.querySelectorAll("tr"));

    searchInput.addEventListener("input", function () {
        const query = this.value.toLowerCase().trim();

        rows.forEach(row => {
            // 2nd column = Patient Name column
            const nameCell = row.querySelector("td:nth-child(2)");
            if (!nameCell) return;

            const nameText = nameCell.innerText.toLowerCase();
            row.style.display = nameText.includes(query) ? "" : "none";
        });
    });
});
