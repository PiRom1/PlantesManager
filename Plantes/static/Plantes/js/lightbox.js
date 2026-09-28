// Visionneuse : agrandit une image dans une boîte de dialogue plein écran.
//
// Balisage attendu :
//   <a href="/media/photo.jpg" data-lightbox data-caption="Monstera deliciosa">
//       <img ...>
//   </a>
// Une seule boîte est créée pour toute la page ; Échap, le bouton ou un clic
// en dehors de l'image la ferment.

function createLightbox() {

    const dialog = document.createElement('dialog');
    dialog.className = 'lightbox';
    dialog.innerHTML = `
        <button class="lightbox__close" type="button" aria-label="Fermer">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
                <path d="M6 6l12 12M18 6L6 18"/>
            </svg>
        </button>
        <figure class="lightbox__figure">
            <div class="lightbox__frame"><img alt=""></div>
            <figcaption class="lightbox__caption"></figcaption>
        </figure>
    `;

    dialog.querySelector('.lightbox__close').addEventListener('click', () => dialog.close());

    // Clic sur le fond (hors de l'image et de sa légende) : fermeture
    dialog.addEventListener('click', event => {
        if (!event.target.closest('.lightbox__figure')) {
            dialog.close();
        }
    });

    document.body.appendChild(dialog);
    return dialog;
}


const links = document.querySelectorAll('a[data-lightbox]');

if (links.length) {
    const dialog = createLightbox();
    const image = dialog.querySelector('img');
    const caption = dialog.querySelector('.lightbox__caption');

    links.forEach(link => {
        link.addEventListener('click', event => {
            event.preventDefault();

            image.src = link.href;
            image.alt = link.dataset.caption || '';
            caption.textContent = link.dataset.caption || '';

            dialog.showModal();
        });
    });
}
