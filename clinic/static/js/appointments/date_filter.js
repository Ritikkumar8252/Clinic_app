function setDate(type) {
    const input = document.getElementById("dateFilter");
    const today = new Date();
    let d = new Date();

    if (type === "yesterday") d.setDate(today.getDate() - 1);
    if (type === "today") d = today;
    if (type === "tomorrow") d.setDate(today.getDate() + 1);

    input.value = d.toISOString().split("T")[0];
}
