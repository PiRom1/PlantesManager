// Affiche les champs de détail correspondant à l'action sélectionnée.
// Tous les groupes sont dans la page ; on ne montre que celui qui correspond.

function showDetailFields() {

    const actionSelect = document.getElementById('id_action');
    const groups = document.querySelectorAll('[data-action-fields]');

    groups.forEach(group => {
        group.hidden = group.dataset.actionFields !== actionSelect.value;
    });
}


const actionSelect = document.getElementById('id_action');

if (actionSelect) {
    actionSelect.addEventListener('change', showDetailFields);
    showDetailFields();
}
