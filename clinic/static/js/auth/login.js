// LOGIN PAGE JS

document.addEventListener("DOMContentLoaded", () => {

    const pwd = document.getElementById("password");
    const toggle = document.getElementById("togglePwd");

    toggle.addEventListener("click", () => {
        const isVisible = pwd.type === "text";
        pwd.type = isVisible ? "password" : "text";
        toggle.textContent = isVisible ? "Show" : "Hide";
    });

});
