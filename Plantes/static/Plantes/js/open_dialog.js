// Ouverture des boîtes de dialogue.
//
// Balisage attendu :
//   <button data-opens="dialog-history">
//   <dialog id="dialog-history" data-open-on-load>   (ouverte dès le chargement,
//                                                     ex. formulaire en erreur)

document.querySelectorAll('[data-opens]').forEach(button => {
    button.addEventListener('click', () => {
        document.getElementById(button.dataset.opens).showModal();
    });
});

document.querySelectorAll('dialog[data-open-on-load]').forEach(dialog => dialog.showModal());
