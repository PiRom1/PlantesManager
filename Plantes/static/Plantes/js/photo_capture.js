// Prise de photo : un champ fichier caché avec `capture` ouvre l'appareil
// photo sur mobile (sur ordinateur, le sélecteur de fichiers habituel). La
// photo prise est recopiée dans le champ visible, qui seul est envoyé.
//
// Balisage attendu :
//   <input type="file" id="id_image">
//   <button type="button" data-captures-for="id_image">
//   <input type="file" capture="environment" hidden data-capture-for="id_image">

document.querySelectorAll('[data-captures-for]').forEach(button => {
    const target = document.getElementById(button.dataset.capturesFor);
    const camera = document.querySelector(`[data-capture-for="${button.dataset.capturesFor}"]`);

    button.addEventListener('click', () => camera.click());

    camera.addEventListener('change', () => {
        if (!camera.files.length) {
            return;
        }

        const transfer = new DataTransfer();
        transfer.items.add(camera.files[0]);
        target.files = transfer.files;
        camera.value = '';
    });
});
