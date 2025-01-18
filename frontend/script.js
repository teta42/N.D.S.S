const url = 'http://127.0.0.1:8000/'

function get_notes() {
    fetch(`${url}/note/getnotes/`)
    .then(response => {
        if (!response.ok) {
            throw new Error('Статус ошибки: ' + response.status);
        }
        return response.json();
    })
    .then(data => {
        add_notes(data);
    })
    .catch(error => {
        console.error('Произошла ошибка: ', error);
    });
}

function add_notes(data) {
    data = data.object[0]
    console.log(data);
    console.log(data.mod)

    const newDiv = document.createElement('div');

    newDiv.classList.add('card');

    newDiv.innerText = `Загаловок: Будет\n${data.content}\n${data.created_at}\n${data.dead_line}\n${data.mod}\nСколько смотрели : Будет`;

    const container = document.getElementById('cardContainer');
    container.appendChild(newDiv);

}

document.addEventListener("DOMContentLoaded", function() {
    get_notes();
});