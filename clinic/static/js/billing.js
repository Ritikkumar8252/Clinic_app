document.addEventListener("click", function (e) {

    // Close all menus first
    document.querySelectorAll(".menu-dropdown").forEach(dd => dd.style.display = "none");

    // If clicked button
    if (e.target.classList.contains("menu-btn")) {

        let dropdown = e.target.nextElementSibling;
        dropdown.style.display = dropdown.style.display === "block" ? "none" : "block";

        e.stopPropagation();   // Prevent closing instantly
        return;
    }
});



// modal functions for payments
function openPaymentModal() {
    const m = document.getElementById("paymentModal");
    if (m) m.style.display = "flex";
}
function closePaymentModal(){
    const m = document.getElementById("paymentModal");
    if (m) m.style.display = "none";
}

// close on ESC
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closePaymentModal();
});
