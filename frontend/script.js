const cardContainer = document.getElementById('cardContainer');
const addCardButton = document.getElementById('create-note');

let a = 4

function add_card() {
    console.log(`Добавленна карточка ${a}`)
    a += 4
    for (let i = 0; i < 4; i++) {
        const newCard = document.createElement('div');
        newCard.className = 'card';
        newCard.textContent = `Карточка ${cardContainer.children.length + 1}`;
        cardContainer.appendChild(newCard);
    }
}



addCardButton.addEventListener('click', () => {
    add_card()
});


cardContainer.addEventListener('scroll', () => {
    const { scrollTop, scrollHeight, clientHeight } = cardContainer;
    if (scrollTop + clientHeight <= scrollHeight) {
        if (a <= 666) {
            console.log('Прокручиваемый элемент достиг низа!');
            add_card()
        } else {
            console.error('Больше карточек нет!')
        }
    }
});