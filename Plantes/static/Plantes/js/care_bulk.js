// Entretien groupé : les plantes n'apparaissent qu'une fois l'action choisie ;
// cases à cocher par plante et par emplacement, compteur, bouton d'envoi actif
// seulement avec au moins une plante, et précisions par plante.
//
// Les précisions ne sont pas dans la page au chargement (une centaine de
// plantes fois tous les champs de toutes les actions, ce serait lourd) : un
// gabarit <template> est cloné au premier clic sur « Préciser », « p__ »
// remplacé par « p<id> » dans les noms et identifiants, puis prérempli avec
// le commun du lot. Tant qu'un champ précisé n'a pas été touché, il suit les
// changements du commun. Les champs clonés sont confiés à tags_input.js et
// care_detail.js, chargés avant.
//
// Balisage attendu :
//   <form data-care>
//       <section data-common>                                 (action, options, commentaire)
//           <select id="id_action">
//       <section data-needs-action>                           (masquée sans action)
//       <input type="checkbox" data-all>                      (toutes les plantes)
//       <details data-group>
//           <input type="checkbox" data-group-all>            (celles de l'emplacement)
//           <span data-group-count></span>
//           <div data-plant="12">
//               <input type="checkbox" name="plants" value="12">
//               <button data-refine>
//               <div data-override hidden>
//       <span data-count></span>
//       <button data-submit>
//   <template id="care-override">

const careForm = document.querySelector('[data-care]');

if (careForm) {

    const actionSelect = document.getElementById('id_action');
    const common = careForm.querySelector('[data-common]');
    const template = document.getElementById('care-override');
    const boxes = [...careForm.querySelectorAll('input[name="plants"]')];
    const allBox = careForm.querySelector('[data-all]');
    const counters = careForm.querySelectorAll('[data-count]');
    const submit = careForm.querySelector('[data-submit]');

    function setGroupBox(box, checked, total) {
        box.checked = total > 0 && checked === total;
        box.indeterminate = checked > 0 && checked < total;
    }

    function refresh() {
        const checked = boxes.filter(box => box.checked).length;

        counters.forEach(counter => {
            counter.textContent = checked === 0 ? 'Aucune plante cochée'
                : checked === 1 ? '1 plante cochée' : `${checked} plantes cochées`;
        });

        submit.disabled = checked === 0 || !actionSelect.value;
        setGroupBox(allBox, checked, boxes.length);

        careForm.querySelectorAll('[data-needs-action]').forEach(section => {
            section.hidden = !actionSelect.value;
        });

        careForm.querySelectorAll('[data-group]').forEach(group => {
            const inside = [...group.querySelectorAll('input[name="plants"]')];
            const count = inside.filter(box => box.checked).length;

            setGroupBox(group.querySelector('[data-group-all]'), count, inside.length);
            group.querySelector('[data-group-count]').textContent = `${count} / ${inside.length}`;
        });
    }

    function checkAll(list, checked) {
        list.forEach(box => { box.checked = checked; });
        refresh();
    }

    allBox.addEventListener('change', () => checkAll(boxes, allBox.checked));

    careForm.querySelectorAll('[data-group]').forEach(group => {
        const head = group.querySelector('[data-group-all]');
        head.addEventListener('change', () => checkAll([...group.querySelectorAll('input[name="plants"]')], head.checked));
    });

    boxes.forEach(box => box.addEventListener('change', refresh));
    actionSelect.addEventListener('change', refresh);

    // Nom d'un champ précisé sans son préfixe : celui de son homologue du commun
    function baseName(field, prefix) {
        return field.name.startsWith(`${prefix}-`) ? field.name.slice(prefix.length + 1) : null;
    }

    // Levé pendant une recopie : l'événement qu'elle déclenche n'est pas un geste
    let syncing = false;

    function copyValue(field, source) {
        if (field.type === 'checkbox') {
            field.checked = source.checked;
        } else {
            field.value = source.value;
        }

        // Un champ conditionnel du clone écoute son pilote (care_detail.js)
        syncing = true;
        field.dispatchEvent(new Event('change', { bubbles: true }));
        syncing = false;
    }

    // Préremplissage : chaque champ prend la valeur de son homologue du commun
    // et reste synchronisé avec lui (data-synced) jusqu'au premier geste dessus
    function prefill(block, prefix) {
        block.querySelectorAll('[data-tags-input]').forEach(container => {
            const source = common.querySelector(`[data-tags-input][data-name="${container.dataset.name.slice(prefix.length + 1)}"]`);
            const input = container.querySelector('.tags__input');

            source.querySelectorAll('.tags__chip').forEach(chip => {
                const copy = chip.cloneNode(true);
                copy.querySelector('input[type="hidden"]').name = container.dataset.name;
                container.insertBefore(copy, input);
            });
        });

        block.querySelectorAll('input, select, textarea').forEach(field => {
            const name = baseName(field, prefix);
            const source = name && field.type !== 'hidden' ? common.querySelector(`[name="${name}"]`) : null;

            if (source && field.type !== 'file') {
                copyValue(field, source);
            }

            field.dataset.synced = '';
        });
    }

    // Précisions : clonées à la demande, la plante est cochée du même coup
    function fillOverride(plant, block) {
        const prefix = `p${plant.dataset.plant}`;

        block.innerHTML = template.innerHTML.replaceAll('p__', prefix);
        prefill(block, prefix);

        block.querySelectorAll('[data-tags-input]').forEach(setupTagsInput);
        block.querySelectorAll('[data-shown-when]').forEach(setupDependentField);
        block.querySelectorAll('[data-action-fields]').forEach(group => {
            group.hidden = group.dataset.actionFields !== actionSelect.value;
        });

        // Un champ touché ne suit plus le commun ; la ligne le signale, même repliée
        ['input', 'change'].forEach(type => block.addEventListener(type, event => {
            if (!syncing) {
                delete event.target.dataset.synced;
                plant.classList.add('care-plant--refined');
            }
        }));
    }

    // Le commun change : les champs précisés jamais touchés suivent
    common.addEventListener('input', event => {
        const source = event.target;

        if (!source.name) {
            return;
        }

        careForm.querySelectorAll('[data-plant]').forEach(plant => {
            const prefix = `p${plant.dataset.plant}`;

            plant.querySelectorAll('[data-override] [data-synced]').forEach(field => {
                if (baseName(field, prefix) === source.name) {
                    copyValue(field, source);
                }
            });
        });
    });

    careForm.querySelectorAll('[data-refine]').forEach(button => {
        const plant = button.closest('[data-plant]');
        const block = plant.querySelector('[data-override]');

        button.addEventListener('click', () => {
            if (!block.children.length) {
                fillOverride(plant, block);
            }

            block.hidden = !block.hidden;
            button.setAttribute('aria-expanded', String(!block.hidden));
            button.textContent = block.hidden ? 'Préciser' : 'Replier';

            if (!block.hidden) {
                plant.querySelector('input[name="plants"]').checked = true;
                refresh();
            }
        });
    });

    refresh();
}
