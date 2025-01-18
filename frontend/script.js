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
    const inter = data.object
    for (const note of inter) {
        // data = data.object[0]
        console.log(note);
        console.log(note.mod)

        const newNote = document.createElement('button');

        newNote.classList.add('card');

        newNote.innerText = `Загаловок: Будет\n${note.content}\n${note.created_at}\n${note.dead_line}\n${note.mod}\nСколько смотрели : Будет`;

        const container = document.getElementById('cardContainer');
        container.appendChild(newNote);
    }
}

document.addEventListener("DOMContentLoaded", function() {
    get_notes();
});