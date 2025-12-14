function initTagInput(field) {

    const tagsBox = document.getElementById(field + "-tags");
    const input = document.getElementById(field + "-input");
    const hidden = document.getElementById(field + "-hidden");

    if (!tagsBox || !input || !hidden) return;

    if (hidden.value.trim()) {
        hidden.value.split(",").forEach(t => addTag(t.trim()));
    }

    function addTag(text) {
        if (!text) return;

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
        hidden.value = [...tagsBox.children]
            .map(t => t.dataset.val)
            .join(",");
    }

    input.addEventListener("keydown", e => {
        if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            addTag(input.value.trim());
            input.value = "";
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initTagInput("symptoms");
    initTagInput("diagnosis");
    initTagInput("advice");
});
