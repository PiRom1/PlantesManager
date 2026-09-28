// Barre de recherche du catalogue : recharge la page avec ?q=... après une
// pause de frappe, pour ne pas envoyer une requête à chaque caractère.
//
// Balisage attendu :
//   <form data-search-form><input type="search" name="q"></form>

const SEARCH_DELAY_MS = 1500;

const form = document.querySelector('[data-search-form]');

if (form) {
    const input = form.querySelector('input[name="q"]');
    let timer = null;

    input.addEventListener('input', () => {
        clearTimeout(timer);
        timer = setTimeout(() => form.requestSubmit(), SEARCH_DELAY_MS);
    });

    // Entrée valide tout de suite, sans attendre le délai
    form.addEventListener('submit', () => clearTimeout(timer));
}
