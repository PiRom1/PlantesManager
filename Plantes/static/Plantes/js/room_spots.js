// Pièce puis emplacement, dans le formulaire plante : le champ emplacement
// n'apparaît qu'une fois la pièce choisie, et ne propose que les siens.
// Sans pièce, il reste invisible (sa place est réservée) mais garde un éventuel emplacement sans pièce
// (plante enregistrée avant les pièces) : il n'est pas perdu à l'enregistrement.
//
// Les options sont retirées du menu, pas masquées : Safari sur iPhone ignore
// l'attribut hidden des options.
//
// Balisage attendu :
//   <div data-room-select="id_room" data-spot-select="id_spot"
//        data-dialog-room="id_spot_room">        (menu des pièces de la boîte « Nouvel emplacement »,
//                                                 qui s'ouvre ainsi sur la pièce choisie)
//   <select id="id_spot">
//       <option value="7" data-room="3">         (pièce de l'emplacement, vide s'il n'en a pas)
//
// Une pièce ou un emplacement créé à la volée arrive par l'événement
// « quick-add » de quick_add.js : un nouvel emplacement fait suivre la pièce.

document.querySelectorAll('[data-room-select]').forEach(wrapper => {

    const roomSelect = document.getElementById(wrapper.dataset.roomSelect);
    const spotSelect = document.getElementById(wrapper.dataset.spotSelect);
    const dialogRoom = document.getElementById(wrapper.dataset.dialogRoom);
    const spotField = spotSelect.closest('.field');

    // L'option vide (« --------- ») n'a pas de pièce : elle reste toujours
    const allSpots = [...spotSelect.options];

    function filter() {
        const room = roomSelect.value;
        const chosen = spotSelect.value;
        const shown = allSpots.filter(option => option.value === '' || option.dataset.room === room);

        spotSelect.replaceChildren(...shown);
        spotSelect.value = shown.some(option => option.value === chosen) ? chosen : '';
        spotField.classList.toggle('field--pending', room === '');

        if (dialogRoom) {
            dialogRoom.value = room;
        }
    }

    roomSelect.addEventListener('change', filter);
    roomSelect.addEventListener('quick-add', filter);

    spotSelect.addEventListener('quick-add', event => {
        const option = spotSelect.selectedOptions[0];
        option.dataset.room = event.detail.room ?? '';
        allSpots.push(option);

        roomSelect.value = option.dataset.room;
        filter();
    });

    filter();
});
