// Autocomplétion sur un champ texte : interroge une URL JSON après une pause
// de frappe, et écrit l'identifiant choisi dans un champ caché.
//
// Balisage attendu :
//   <input type="text"   data-autocomplete-url="..." data-target="id_specie">
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

    function showSuggestions(results) {
        clearSuggestions();

        if (results.length === 0) {
            suggestions.innerHTML = '<li>Aucun résultat</li>';
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
            .then(data => showSuggestions(data.results));
    }

    input.addEventListener('input', () => {
        // Le choix précédent ne vaut plus dès que le texte change
        hiddenField.value = '';

        clearTimeout(timer);
        timer = setTimeout(search, TYPING_DELAY_MS);
    });
}


document.querySelectorAll('[data-autocomplete-url]').forEach(setupAutocomplete);
