document.addEventListener("DOMContentLoaded", () => {
    try {
        const dataEl = document.getElementById("chart-data");
        const canvas = document.getElementById("patientChart");

        if (!dataEl || !canvas) return;

        const labels = JSON.parse(dataEl.dataset.labels || "[]");
        const values = JSON.parse(dataEl.dataset.values || "[]");

        if (!Array.isArray(labels) || labels.length === 0) return;
        if (!window.Chart) return;

        new Chart(canvas, {
            type: "line",
            data: {
                labels: labels,
                datasets: [{
                    label: "Patients",
                    data: values,
                    borderColor: "#2563eb",
                    backgroundColor: "rgba(37,99,235,0.1)",
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } }
            }
        });

    } catch (err) {
        console.error("Dashboard chart error:", err);
    }
});
