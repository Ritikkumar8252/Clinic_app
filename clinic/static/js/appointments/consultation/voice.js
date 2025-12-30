// ===============================
// VOICE DICTATION (SAFE + SIMPLE)
// ===============================

window.voice = {
    recognition: null,
    activeInput: null,
    listening: false
};

function startVoice(inputId, btn) {

    if (!('webkitSpeechRecognition' in window)) {
        alert("Voice dictation not supported in this browser");
        return;
    }

    // stop if already running
    if (voice.listening) {
        stopVoice(btn);
        return;
    }

    const input = document.getElementById(inputId);
    if (!input) return;

    voice.activeInput = input;
    voice.recognition = new webkitSpeechRecognition();

    voice.recognition.lang = "en-IN"; // English India
    voice.recognition.continuous = true;
    voice.recognition.interimResults = true;

    let finalText = "";

    voice.recognition.onstart = () => {
        voice.listening = true;
        btn.classList.add("mic-active");
        input.classList.add("voice-active");
    };

    voice.recognition.onresult = (event) => {
        let interim = "";

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;

            if (event.results[i].isFinal) {
                finalText += transcript + " ";
            } else {
                interim += transcript;
            }
        }

        input.value = finalText + interim;
    };

    voice.recognition.onerror = () => {
        stopVoice(btn);
    };

    voice.recognition.onend = () => {
        stopVoice(btn);
        autoSave(); // trigger your existing autosave
    };

    voice.recognition.start();
}

function stopVoice(btn) {
    if (voice.recognition) {
        voice.recognition.stop();
    }

    voice.listening = false;

    if (btn) btn.classList.remove("mic-active");
    if (voice.activeInput) {
        voice.activeInput.classList.remove("voice-active");
    }
}
