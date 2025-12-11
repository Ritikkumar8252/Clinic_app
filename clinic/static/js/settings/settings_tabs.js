function switchTab(tabName, el) {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));

    document.getElementById(tabName).classList.add("active");
    el.classList.add("active");
}
