// Update total
function updateTotal() {
    let total = 0;
    document.querySelectorAll(".amount-field").forEach(input => {
        total += Number(input.value) || 0;
    });
    document.getElementById("totalAmount").value = total;
}

// Add new row
document.getElementById("addRowBtn").addEventListener("click", () => {
    const row = document.createElement("tr");
    row.innerHTML = `
        <td><input type="text" name="item_name[]" required></td>
        <td><input type="number" name="item_amount[]" class="amount-field" required></td>
        <td><button type="button" class="remove-btn remove-item">×</button></td>
    `;
    document.getElementById("itemsBody").appendChild(row);
});

// Listen for amount changes
document.addEventListener("input", (e) => {
    if (e.target.classList.contains("amount-field")) {
        updateTotal();
    }
});

// Remove row
document.addEventListener("click", (e) => {
    if (e.target.classList.contains("remove-item")) {
        e.target.closest("tr").remove();
        updateTotal();
    }
});
