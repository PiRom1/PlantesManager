// Affiche les champs de détail correspondant à l'action sélectionnée.
// Tous les groupes sont dans la page ; on ne montre que celui qui correspond.
//
// Dans un groupe, un champ peut dépendre d'un autre : il n'apparaît que pour
// certaines valeurs du champ pilote (ex. parasites et gravité d'une inspection,
// seulement en cas de suspicion ou de présence).
//
// Balisage attendu :
//   <fieldset data-action-fields="<id action>">
//   <div class="field" data-shown-when="<id du select pilote>" data-shown-values="SUSPICION CONFIRMED">

function showDetailFields() {

    const actionSelect = document.getElementById('id_action');
    const groups = document.querySelectorAll('[data-action-fields]');

    groups.forEach(group => {
        group.hidden = group.dataset.actionFields !== actionSelect.value;
    });
}


function setupDependentField(field) {

    const pilot = document.getElementById(field.dataset.shownWhen);
    const values = field.dataset.shownValues.split(' ');

    function update() {
        field.hidden = !values.includes(pilot.value);
    }

    pilot.addEventListener('change', update);
    update();
}


const actionSelect = document.getElementById('id_action');

if (actionSelect) {
    actionSelect.addEventListener('change', showDetailFields);
    showDetailFields();
}

document.querySelectorAll('[data-shown-when]').forEach(setupDependentField);
