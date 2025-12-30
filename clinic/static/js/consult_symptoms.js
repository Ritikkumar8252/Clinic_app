const searchInput = document.getElementById("symptomSearch");
const resultsBox = document.getElementById("symptomResults");
const symptomsHidden = document.getElementById("symptoms-hidden");

let timer = null;

if (searchInput && resultsBox && symptomsHidden) {

    searchInput.addEventListener("input", () => {
        clearTimeout(timer);

        const q = searchInput.value.trim();
        if (!q) {
            resultsBox.innerHTML = "";
            return;
        }

        timer = setTimeout(() => {
            fetch(`/symptom-templates/search?q=${encodeURIComponent(q)}`)
                .then(res => res.json())
                .then(data => {
                    resultsBox.innerHTML = "";

                    data.forEach(t => {
                        const div = document.createElement("div");
                        div.className = "template-item";
                        div.innerText = t.name;

                        div.onclick = () => {
                            // 🔑 SINGLE SOURCE OF TRUTH
                            symptomsHidden.value = t.content;

                            // rebuild tags UI
                            rebuildTags("symptoms", t.content);

                            // autosave trigger
                            autoSave();

                            // cleanup UI
                            resultsBox.innerHTML = "";
                            searchInput.value = "";
                        };

                        resultsBox.appendChild(div);
                    });
                });
        }, 300);
    });
}
