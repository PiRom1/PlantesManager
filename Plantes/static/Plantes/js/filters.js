// Barre de filtres : un menu déroulant changé renvoie le formulaire tout seul,
// le champ texte attend Entrée ou le bouton.
//
// Balisage attendu :
//   <form method="get" data-auto-submit>

document.querySelectorAll('form[data-auto-submit] select').forEach(select => {
    select.addEventListener('change', () => select.form.requestSubmit());
});
