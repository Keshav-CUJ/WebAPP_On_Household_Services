document.addEventListener("DOMContentLoaded", function () {
    const themeToggle = document.getElementById("theme-toggle");
    const html = document.documentElement;
    const themeIcon = themeToggle.querySelector("i");

    // Check for saved theme in localStorage
    const savedTheme = localStorage.getItem("theme") || "light";
    html.setAttribute("data-theme", savedTheme);
    themeIcon.classList.toggle("fa-sun", savedTheme === "dark");
    themeIcon.classList.toggle("fa-moon", savedTheme === "light");

    themeToggle.addEventListener("click", () => {
        let currentTheme = html.getAttribute("data-theme");
        let newTheme = currentTheme === "light" ? "dark" : "light";

        html.setAttribute("data-theme", newTheme);
        themeIcon.classList.toggle("fa-sun", newTheme === "dark");
        themeIcon.classList.toggle("fa-moon", newTheme === "light");

        // Save theme preference in localStorage
        localStorage.setItem("theme", newTheme);
    });
});
