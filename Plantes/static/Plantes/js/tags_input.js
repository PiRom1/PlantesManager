// Champ à choix multiples avec saisie libre : des pastilles, plus un champ
// texte avec suggestions. Entrée ou virgule ajoute une pastille ; chaque
// pastille porte un champ caché du même nom, le serveur reçoit donc la liste.
// Un texte qui correspond à une suggestion est envoyé avec son code.
//
// Balisage attendu (voir _history_form.html) :
//   <div class="tags" data-tags-input data-name="detail_X_pests">
//       <span class="tags__chip">Thrips
//           <button class="tags__remove" type="button">×</button>
//           <input type="hidden" name="detail_X_pests" value="THRIPS">
//       </span>
//       <input type="text" class="tags__input" list="detail_X_pests-choices">
//       <datalist id="detail_X_pests-choices">
//           <option value="Thrips" data-code="THRIPS"></option>
//       </datalist>
//   </div>

function setupTagsInput(container) {

    const input = container.querySelector('.tags__input');
    const options = [...document.getElementById(input.getAttribute('list')).options];
    const name = container.dataset.name;

    function values() {
        return [...container.querySelectorAll('input[type="hidden"]')].map(hidden => hidden.value);
    }

    function addChip(label, value) {
        if (values().includes(value)) {
            return;
        }

        const chip = document.createElement('span');
        chip.className = 'tags__chip';
        chip.append(label);

        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'tags__remove';
        remove.setAttribute('aria-label', `Retirer ${label}`);
        remove.textContent = '×';

        const hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = name;
        hidden.value = value;

        chip.append(remove, hidden);
        container.insertBefore(chip, input);
    }

    // Le texte saisi devient une pastille ; s'il correspond à une suggestion,
    // c'est le code de celle-ci qui est envoyé
    function flush() {
        const text = input.value.replace(/,/g, ' ').trim();
        input.value = '';

        if (!text) {
            return;
        }

        const option = options.find(option => option.value.toLowerCase() === text.toLowerCase());

        if (option) {
            addChip(option.value, option.dataset.code);
        } else {
            addChip(text, text);
        }
    }

    input.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ',') {
            event.preventDefault();
            flush();
        } else if (event.key === 'Backspace' && !input.value) {
            const last = input.previousElementSibling;
            if (last && last.classList.contains('tags__chip')) {
                last.remove();
            }
        }
    });

    // Choix dans les suggestions, ou champ quitté avec du texte dedans
    input.addEventListener('change', flush);

    // Texte encore dans le champ au moment d'envoyer : il compte aussi
    input.form.addEventListener('submit', flush);

    container.addEventListener('click', event => {
        const remove = event.target.closest('.tags__remove');
        if (remove) {
            remove.closest('.tags__chip').remove();
        }
    });
}


document.querySelectorAll('[data-tags-input]').forEach(setupTagsInput);
