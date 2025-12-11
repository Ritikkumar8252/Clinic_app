document.addEventListener("DOMContentLoaded", () => {
    const search = document.getElementById("appSearch");
    const rows = document.querySelectorAll("#appTable tr");
    const visitFilter = document.getElementById("visitTypeFilter");

    // SEARCH
    search.addEventListener("keyup", () => {
        const value = search.value.toLowerCase();
        rows.forEach(r => {
            r.style.display = r.innerText.toLowerCase().includes(value)
                ? ""
                : "none";
        });
    });

    // VISIT TYPE FILTER
    visitFilter.addEventListener("change", () => {
        const val = visitFilter.value.toLowerCase();
        rows.forEach(r => {
            const category = r.cells[3]?.innerText.toLowerCase();
            r.style.display = val === "" || category === val ? "" : "none";
        });
    });
});
