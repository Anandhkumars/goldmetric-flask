document.addEventListener('DOMContentLoaded', async function () {
    function updateTime() {
        const timeElement = document.getElementById("current-time");
        const now = new Date();
        const timeString = now.toLocaleTimeString();
        const dateString = now.toLocaleDateString();
        const hours = now.getHours();

        let greeting = "Welcome!";
        if (hours >= 5 && hours < 12) {
            greeting = "Good Morning, Admin! ☀️";
        } else if (hours >= 12 && hours < 17) {
            greeting = "Good Afternoon, Admin! 🌞";
        } else if (hours >= 17 && hours < 21) {
            greeting = "Good Evening, Admin! 🌇";
        } else {
            greeting = "Good Night, Admin! 🌙";
        }

        timeElement.textContent = `${dateString} ${timeString} - ${greeting}`;
    }
    setInterval(updateTime, 1000);

    let menu = document.getElementById('menu-toggle');
    let sidebar = document.querySelector('.sidebar');
    let mainContent = document.querySelector('.main-content');

    if (menu && sidebar && mainContent) {
        menu.onclick = function () {
            sidebar.classList.toggle('active');
            mainContent.classList.toggle('active');
        };
    } else {
        console.error('Menu, sidebar, or mainContent elements are missing in the DOM.');
    }

    updateTime();
});