// Menu contextuel : clic droit sur un élément affiche un petit menu à la
// souris. Un élément du menu peut ouvrir un sélecteur de fichier, dont le
// formulaire est envoyé dès qu'un fichier est choisi.
//
// Balisage attendu :
//   <figure data-context-menu="menu-plant-image">...</figure>
//   <div class="context-menu" id="menu-plant-image" hidden>
//       <button data-picks-file="plant-image-input">Changer la photo</button>
//   </div>
//   <form hidden><input type="file" id="plant-image-input" data-submits-on-change></form>

function closeMenus() {
    document.querySelectorAll('.context-menu').forEach(menu => { menu.hidden = true; });
}


document.querySelectorAll('[data-context-menu]').forEach(target => {

    const menu = document.getElementById(target.dataset.contextMenu);

    target.addEventListener('contextmenu', event => {
        event.preventDefault();
        closeMenus();

        menu.hidden = false;

        // Le menu reste dans la fenêtre, même près des bords
        const x = Math.min(event.clientX, window.innerWidth - menu.offsetWidth - 8);
        const y = Math.min(event.clientY, window.innerHeight - menu.offsetHeight - 8);

        menu.style.left = `${x}px`;
        menu.style.top = `${y}px`;
    });
});


document.querySelectorAll('[data-picks-file]').forEach(button => {
    button.addEventListener('click', () => {
        closeMenus();
        document.getElementById(button.dataset.picksFile).click();
    });
});


document.querySelectorAll('[data-submits-on-change]').forEach(input => {
    input.addEventListener('change', () => {
        if (input.files.length) {
            input.form.submit();
        }
    });
});


document.addEventListener('click', closeMenus);
document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
        closeMenus();
    }
});
