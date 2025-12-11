function initTagInput(field) {
    const wrapper = document.getElementById(field + "-wrapper");
    const tagsBox = document.getElementById(field + "-tags");
    const input = document.getElementById(field + "-input");
    const hidden = document.getElementById(field + "-hidden");

    if (hidden.value.trim() !== "") {
        hidden.value.split(",").forEach(t => addTag(t.trim()));
    }

    function addTag(text) {
        text = text.trim();
        if (!text) return;

        const exists = [...tagsBox.children].some(el => el.dataset.val === text);
        if (exists) return;

        const tag = document.createElement("span");
        tag.className = "tag";
        tag.dataset.val = text;
        tag.innerHTML = `${text}<span class="remove">✕</span>`;

        tag.querySelector(".remove").onclick = () => {
            tag.remove();
            updateHidden();
            autoSave();
        };

        tagsBox.appendChild(tag);
        updateHidden();
        autoSave();
    }

    function updateHidden() {
        hidden.value = [...tagsBox.children].map(t => t.dataset.val).join(",");
    }

    input.addEventListener("keydown", function(e) {
        if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            addTag(input.value);
            input.value = "";
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initTagInput("symptoms");
    initTagInput("diagnosis");
    initTagInput("advice");
});
