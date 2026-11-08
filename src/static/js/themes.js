const lightIcon = document.getElementById("lightIcon");
const darkIcon = document.getElementById("darkIcon");
const solarIcon = document.getElementById("solarIcon");
const body = document.body;

function switchTheme(theme){
    body.classList.remove("dark", "light", "solar");
    body.classList.add(theme);
    localStorage.setItem("theme", theme)
}

const savedTheme = localStorage.getItem("theme")
if(savedTheme){
    body.classList.add(savedTheme);
}

lightIcon.addEventListener("click", () => switchTheme("light"));
darkIcon.addEventListener("click", () => switchTheme("dark"));
solarIcon.addEventListener("click", () => switchTheme("solar"));


