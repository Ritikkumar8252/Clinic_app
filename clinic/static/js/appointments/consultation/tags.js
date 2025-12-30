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
// ======================================
// REBUILD TAGS FROM STORED VALUE
// ======================================
function rebuildTags(field, value) {

    const tagsBox = document.getElementById(field + "-tags");
    const hidden = document.getElementById(field + "-hidden");

    if (!tagsBox || !hidden) return;

    // clear existing tags
    tagsBox.innerHTML = "";

    if (!value) return;

    // normalize (CSV)
    const items = value
        .split(",")
        .map(v => v.trim())
        .filter(Boolean);

    items.forEach(text => {
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
    });

    hidden.value = items.join(",");

    function updateHidden() {
        hidden.value = [...tagsBox.children]
            .map(t => t.dataset.val)
            .join(",");
    }
}
