let rectangleCount = 0;

function addRectangles(count) {
    const content = document.getElementById('content');
    for (let i = 0; i < count; i++) {
        const rectangle = document.createElement('div');
        rectangle.className = 'rectangle';
        content.appendChild(rectangle);
    }
}

// Изначально добавляем карточки
addRectangles(20);

function checkScroll() {
    const container = document.getElementById('scrollContainer');
    // Проверяем, достигли ли мы дна контейнера
    if (container.scrollTop + container.clientHeight >= container.scrollHeight - 1) {
        addRectangles(5); // Добавляем карточки
    }
}

// Проверяем прокрутку
document.getElementById('scrollContainer').addEventListener('scroll', checkScroll);
