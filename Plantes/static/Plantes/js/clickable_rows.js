// Rend une ligne de tableau entièrement cliquable.
//
// Balisage attendu :
//   <tr data-href="/pot/3/"> ... </tr>
// Un clic sur un lien ou un bouton de la ligne garde son comportement propre.

document.querySelectorAll('tr[data-href]').forEach(row => {
    row.addEventListener('click', event => {
        if (event.target.closest('a, button')) {
            return;
        }
        window.location = row.dataset.href;
    });
});
