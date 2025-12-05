document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("patientSearch");
    const rows = document.querySelectorAll("#patientTable tr");

    searchInput.addEventListener("keyup", function () {
        const value = this.value.toLowerCase();

        rows.forEach(row => {
            const rowText = row.innerText.toLowerCase();
            row.style.display = rowText.includes(value) ? "" : "none";
        });
    });
});
