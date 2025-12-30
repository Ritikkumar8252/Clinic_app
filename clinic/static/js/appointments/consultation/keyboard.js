document.addEventListener("keydown", function (e) {

    const active = document.activeElement;
    if (!active) return;

    const isInput = active.tagName === "INPUT";
    const isTextarea = active.tagName === "TEXTAREA";

    // ---------------------------------------
    // ENTER → NEXT FIELD (except textarea)
    // ---------------------------------------
    if (e.key === "Enter" && !e.shiftKey && !e.ctrlKey) {

        if (isTextarea) return; // textarea allow newline
        e.preventDefault();
        focusNext(active);
    }

    // ---------------------------------------
    // SHIFT + ENTER → newline in textarea
    // ---------------------------------------
    if (e.key === "Enter" && e.shiftKey && isTextarea) {
        return; // default behaviour
    }

    // ---------------------------------------
    // ARROW DOWN → NEXT FIELD
    // ---------------------------------------
    if (e.key === "ArrowDown") {
        e.preventDefault();
        focusNext(active);
    }

    // ---------------------------------------
    // ARROW UP → PREVIOUS FIELD
    // ---------------------------------------
    if (e.key === "ArrowUp") {
        e.preventDefault();
        focusPrev(active);
    }

    // ---------------------------------------
    // CTRL + ENTER → ADD MEDICINE ROW
    // ---------------------------------------
    if (e.key === "Enter" && e.ctrlKey) {
        const addBtn = document.getElementById("addRowBtn");
        if (addBtn) {
            e.preventDefault();
            addBtn.click();
        }
    }

    // ---------------------------------------
    // ESC → CLOSE TEMPLATE POPUPS
    // ---------------------------------------
    if (e.key === "Escape") {
        document.querySelectorAll(".template-popup")
            .forEach(box => box.style.display = "none");
    }
});

// ============================
// HELPERS
// ============================

function getFocusableElements() {
    return Array.from(
        document.querySelectorAll(
            "input:not([disabled]), textarea:not([disabled])"
        )
    ).filter(el => el.offsetParent !== null);
}

function focusNext(current) {
    const fields = getFocusableElements();
    const index = fields.indexOf(current);
    if (index >= 0 && index < fields.length - 1) {
        fields[index + 1].focus();
    }
}

function focusPrev(current) {
    const fields = getFocusableElements();
    const index = fields.indexOf(current);
    if (index > 0) {
        fields[index - 1].focus();
    }
}
