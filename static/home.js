document.addEventListener("DOMContentLoaded", function() {
    const progressFill = document.getElementById('progress-fill');
    const badge = document.getElementById('percentage-badge');
    const splashScreen = document.getElementById('splash-screen');
    let progress = 0;

    const interval = setInterval(() => {
        progress += 1.5; 
        if (progress > 100) progress = 100;

        if (progressFill) progressFill.style.width = `${progress}%`;
        if (badge) badge.innerText = `${Math.round(progress)}%`;

        if (progress >= 100) {
            clearInterval(interval);
            setTimeout(() => {
                if (splashScreen) splashScreen.style.transform = "translateY(-100%)";
                document.body.classList.remove('no-scroll'); 
            }, 500);
        }
    }, 20);
});

function filterCategories() {
    let query = document.getElementById('search-input').value.toLowerCase();
    let items = document.querySelectorAll('.cuisine-item, .restaurant-item, .dessert-item');
    items.forEach(function(item) {
        let itemName = item.querySelector('h3').textContent.toLowerCase();
        if (itemName.includes(query)) {
            item.style.display = 'block'; 
        } else {
            item.style.display = 'none';
        }
    });
}