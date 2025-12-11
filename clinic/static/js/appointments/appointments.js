document.addEventListener("DOMContentLoaded", () => {

    // TAB SWITCHING
    const tabs = document.querySelectorAll("#appointmentTabs .nav-link");
    const sections = document.querySelectorAll(".appointment-section");

    tabs.forEach(tab => {
        tab.addEventListener("click", () => {

            tabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");

            sections.forEach(sec => sec.classList.add("d-none"));
            document.getElementById(tab.dataset.section).classList.remove("d-none");
        });
    });

    // CARD MOVEMENT
    document.addEventListener("click", (e) => {

        // Start Consultation
        if (e.target.classList.contains("start-btn")) {
            let card = e.target.closest(".appointment-card");
            document.getElementById("started").appendChild(card);

            card.style.background = "#d4edda";
            card.querySelector(".card-actions").innerHTML = `
                <button class="btn btn-sm btn-success finish-btn">Finish</button>
                <button class="btn btn-sm btn-outline-danger cancel-btn">Cancel</button>
            `;
        }

        // Finish Consultation
        if (e.target.classList.contains("finish-btn")) {
            let card = e.target.closest(".appointment-card");
            document.getElementById("finished").appendChild(card);

            card.style.background = "#e2e3e5";
            card.querySelector(".card-actions").innerHTML = `<span class="text-muted">Done</span>`;
        }

        // Cancel Consultation
        if (e.target.classList.contains("cancel-btn")) {
            let card = e.target.closest(".appointment-card");
            document.getElementById("cancelled").appendChild(card);

            card.style.background = "#f8d7da";
            card.querySelector(".card-actions").innerHTML = `<span class="text-danger">Cancelled</span>`;
        }
    });

});
