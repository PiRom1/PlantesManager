// Création rapide d'un emplacement ou d'un pot depuis le formulaire plante.
// Le formulaire de la popup est envoyé en arrière-plan ; l'objet créé est
// ajouté au menu déroulant correspondant, puis sélectionné.
//
// Balisage attendu :
//   <button data-opens="dialog-spot">
//   <dialog id="dialog-spot" data-post-url="..." data-target="id_spot">
//       <form> ... </form>
//   </dialog>

function getCookie(name) {
    const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
    return match ? match[2] : '';
}


function setupQuickAdd(dialog) {

    const form = dialog.querySelector('form');
    const select = document.getElementById(dialog.dataset.target);
    const errors = dialog.querySelector('[data-errors]');

    form.addEventListener('submit', event => {
        event.preventDefault();
        errors.textContent = '';

        fetch(dialog.dataset.postUrl, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: new FormData(form),
        })
            .then(response => response.json().then(data => ({ ok: response.ok, data })))
            .then(({ ok, data }) => {

                if (!ok) {
                    errors.textContent = 'Formulaire invalide : ' + Object.keys(data.errors).join(', ');
                    return;
                }

                const option = new Option(data.name, data.id, true, true);
                select.add(option);

                form.reset();
                dialog.close();
            });
    });
}


document.querySelectorAll('[data-opens]').forEach(button => {
    button.addEventListener('click', () => {
        document.getElementById(button.dataset.opens).showModal();
    });
});

document.querySelectorAll('dialog[data-post-url]').forEach(setupQuickAdd);
