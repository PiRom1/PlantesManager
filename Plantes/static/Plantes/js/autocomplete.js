// Autocomplétion sur un champ texte : interroge une URL JSON après une pause
// de frappe, et écrit l'identifiant choisi dans un champ caché.
//
// Sans résultat, peut proposer de créer l'objet manquant dans une boîte de
// dialogue, avec le texte tapé déjà recopié dans l'un de ses champs.
//
// Balisage attendu :
//   <input type="text"   data-autocomplete-url="..." data-target="id_specie"
//          data-create-dialog="dialog-specie" data-create-field="vernacular_name">  (les deux derniers optionnels)
//   <ul    data-suggestions-for="id_specie"></ul>
//   <input type="hidden" name="specie" id="id_specie">

const TYPING_DELAY_MS = 1000;
const MIN_LENGTH = 2;


function setupAutocomplete(input) {

    const hiddenField = document.getElementById(input.dataset.target);
    const suggestions = document.querySelector(`[data-suggestions-for="${input.dataset.target}"]`);

    let timer = null;

    function clearSuggestions() {
        suggestions.innerHTML = '';
    }

    function choose(result) {
        hiddenField.value = result.id;
        input.value = result.label;
        clearSuggestions();
    }

    // Ouvre la boîte de création avec le texte cherché déjà en place
    function offerCreation(item, query) {
        const dialog = document.getElementById(input.dataset.createDialog);
        const link = document.createElement('a');

        link.href = '#';
        link.textContent = `Créer l'espèce « ${query} »`;
        link.addEventListener('click', event => {
            event.preventDefault();
            clearSuggestions();

            if (input.dataset.createField) {
                dialog.querySelector('form').elements[input.dataset.createField].value = query;
            }

            dialog.showModal();
        });

        item.appendChild(link);
    }

    function showSuggestions(results, query) {
        clearSuggestions();

        if (results.length === 0) {
            const item = document.createElement('li');
            item.textContent = 'Aucun résultat. ';

            if (input.dataset.createDialog) {
                offerCreation(item, query);
            }

            suggestions.appendChild(item);
            return;
        }

        results.forEach(result => {
            const item = document.createElement('li');
            const link = document.createElement('a');

            link.href = '#';
            link.textContent = result.label;
            link.addEventListener('click', event => {
                event.preventDefault();
                choose(result);
            });

            item.appendChild(link);
            suggestions.appendChild(item);
        });
    }

    function search() {
        const query = input.value.trim();

        if (query.length < MIN_LENGTH) {
            clearSuggestions();
            return;
        }

        fetch(`${input.dataset.autocompleteUrl}?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => showSuggestions(data.results, query));
    }

    input.addEventListener('input', () => {
        // Le choix précédent ne vaut plus dès que le texte change
        hiddenField.value = '';

        clearTimeout(timer);
        timer = setTimeout(search, TYPING_DELAY_MS);
    });
}


document.querySelectorAll('[data-autocomplete-url]').forEach(setupAutocomplete);
