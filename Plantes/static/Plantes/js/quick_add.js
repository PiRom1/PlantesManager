// Création rapide d'un emplacement, d'un pot ou d'une espèce depuis le
// formulaire plante. Le formulaire de la popup est envoyé en arrière-plan ;
// l'objet créé est sélectionné dans le champ correspondant.
//
// Pour une espèce, le serveur peut répondre 409 avec les espèces du catalogue
// qui ressemblent : la boîte les affiche, « C'est celle-ci » choisit l'une
// d'elles, « Créer quand même » renvoie le formulaire avec confirmed=1.
//
// L'ouverture des boîtes est gérée par open_dialog.js.
//
// Balisage attendu :
//   <button data-opens="dialog-spot">
//   <dialog id="dialog-spot" data-post-url="..." data-target="id_spot">        (menu déroulant)
//   <dialog id="dialog-room" data-post-url="..." data-target="id_spot_room id_room">
//                                                    (plusieurs menus, sélectionné dans chacun)
//   <dialog id="dialog-specie" data-post-url="..." data-target="id_specie"
//           data-label-target="specie-search">                               (champ caché + champ visible)
//       <form>
//           <input type="hidden" name="confirmed" value="">                     (si ressemblance possible)
//           <div data-similar></div>
//           ...
//       </form>
//   </dialog>
//
// Chaque cible reçoit ensuite un événement « quick-add » dont `detail` est la
// réponse du serveur (ex. la pièce d'un emplacement créé, pour room_spots.js).

function getCookie(name) {
    const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
    return match ? match[2] : '';
}


function setupQuickAdd(dialog) {

    const form = dialog.querySelector('form');
    const targets = dialog.dataset.target.split(' ').map(id => document.getElementById(id));
    const label = dialog.dataset.labelTarget ? document.getElementById(dialog.dataset.labelTarget) : null;
    const errors = dialog.querySelector('[data-errors]');
    const similar = dialog.querySelector('[data-similar]');

    // Menu déroulant : l'objet devient une option sélectionnée.
    // Champ caché + champ visible : l'identifiant d'un côté, le libellé de l'autre
    function select(id, name) {
        if (label) {
            targets[0].value = id;
            label.value = name;
        } else {
            targets.forEach(target => target.add(new Option(name, id, true, true)));
        }
    }

    // Après la remise à zéro de la boîte : qui écoute peut y réécrire
    function done(data) {
        select(data.id, data.name);
        form.reset();

        if (similar) {
            similar.replaceChildren();
        }

        targets.forEach(target => target.dispatchEvent(new CustomEvent('quick-add', { detail: data })));
        dialog.close();
    }

    function showSimilar(matches) {
        similar.replaceChildren();

        const intro = document.createElement('p');
        intro.textContent = 'Attention, ton espèce ressemble fort à une espèce du catalogue. Es-tu sûr que ce n\'était pas celle-ci ?';
        similar.appendChild(intro);

        const list = document.createElement('ul');

        matches.forEach(match => {
            const item = document.createElement('li');
            const text = document.createElement('span');
            const choose = document.createElement('button');

            text.textContent = `${match.label} (${match.score} %)`;

            choose.type = 'button';
            choose.className = 'btn btn--small';
            choose.textContent = 'C\'est celle-ci';
            choose.addEventListener('click', () => done({ id: match.id, name: match.label }));

            item.append(text, choose);
            list.appendChild(item);
        });

        similar.appendChild(list);

        const force = document.createElement('button');
        force.type = 'button';
        force.className = 'btn btn--small btn--danger';
        force.textContent = 'Créer quand même';
        force.addEventListener('click', () => {
            form.elements.confirmed.value = '1';
            form.requestSubmit();
        });

        similar.appendChild(force);
    }

    form.addEventListener('submit', event => {
        event.preventDefault();
        errors.textContent = '';

        fetch(dialog.dataset.postUrl, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: new FormData(form),
        })
            .then(response => response.json().then(data => ({ status: response.status, data })))
            .then(({ status, data }) => {

                if (status === 409 && similar) {
                    showSimilar(data.similar);
                    return;
                }

                if (status !== 200) {
                    errors.textContent = 'Formulaire invalide : ' + Object.keys(data.errors || {}).join(', ');
                    return;
                }

                done(data);
            });
    });
}


document.querySelectorAll('dialog[data-post-url]').forEach(setupQuickAdd);
