from datetime import datetime, time

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from Plantes.forms import PlantForm, PlantHistoryForm, PlantImageForm, PotForm, SpotForm
from Plantes.models import Action, DetailFieldType, Plant, PlantHistory, PlantState, Pot, Specie, Spot


def restrict_to_user(form, user):
    """
    Limite les menus déroulants aux objets de l'utilisateur :
    ses emplacements, ses pots et ses plantes (pour la plante mère).
    """

    form.fields['spot'].queryset = Spot.objects.filter(user=user).order_by('name')
    form.fields['pot'].queryset = Pot.objects.filter(user=user).order_by('denomination')
    form.fields['father'].queryset = Plant.objects.filter(user=user)


def selected_specie(form):
    """
    Espèce actuellement retenue par le formulaire, pour préremplir le champ de
    recherche visible (le formulaire, lui, ne transporte que l'identifiant).
    """

    specie_id = form.data.get('specie') or form.initial.get('specie') or form.instance.specie_id

    # L'identifiant vient de l'URL ou du POST : il peut être n'importe quoi
    if not str(specie_id or '').isdigit():
        return None

    return Specie.objects.filter(id=specie_id).first()


def log_arrival(plant):
    """
    Première entrée du journal, qui porte l'état choisi à la création : le
    journal fait foi pour l'état, il doit donc en avoir la trace dès le départ.
    Datée de l'acquisition si elle est connue.
    """

    if plant.acquisition_date:
        date = timezone.make_aware(datetime.combine(plant.acquisition_date, time.min))
    else:
        date = timezone.now()

    PlantHistory.objects.create(plant=plant, state=plant.state, date=date,
                                comment='Arrivée dans la collection')



@login_required
def list_plants(request):


    url = 'Plantes/plants/list_plants.html'

    plants = list(Plant.objects
                  .filter(user=request.user)
                  .select_related('specie', 'state', 'spot', 'pot', 'substrate')
                  .order_by('specie__vernacular_name'))

    # Filtre « parasitées » : /plants/?filter=pests, le statut vient du journal
    pests_only = request.GET.get('filter') == 'pests'
    infested = [plant for plant in plants if plant.pest_episode]

    context = {'all_plants' : infested if pests_only else plants,
               'total' : len(plants), 'infested_count' : len(infested), 'pests_only' : pests_only}

    return render(request, url, context)



@login_required
def add_plant(request):


    url = 'Plantes/plants/add_plant.html'

    if request.method == 'POST':
        form = PlantForm(request.POST, request.FILES)
        restrict_to_user(form, request.user)

        if form.is_valid():
            plant = form.save(commit=False)
            plant.user = request.user
            plant.save()

            if plant.state:
                log_arrival(plant)

            return redirect('detail_plant', id_plant=plant.id)

    else:
        # Préremplissage depuis la fiche espèce : /plant/add/?specie=<id>
        form = PlantForm(initial={'specie': request.GET.get('specie')})
        restrict_to_user(form, request.user)

    context = {'form' : form, 'selected_specie' : selected_specie(form),
               'spot_form' : SpotForm(), 'pot_form' : PotForm()}

    return render(request, url, context)




def build_detail(action, posted):
    """
    Compile en dictionnaire les champs de détail postés pour l'action choisie.

    Les champs du formulaire sont nommés detail_<CODE>_<nom> : tous les groupes
    sont présents dans la page, seul celui de l'action retenue est lu. Le schéma
    vient de Action.DETAIL_FIELDS, jamais d'ailleurs.
    """

    if action is None:
        return {}

    detail = {}

    for field in action.detail_fields:
        key = f'detail_{action.code}_{field.name}'

        if field.type == DetailFieldType.BOOLEAN:
            detail[field.name] = key in posted
            continue

        if field.type == DetailFieldType.TAGS:
            tags = clean_tags(posted.getlist(key), field.choices)
            if tags:
                detail[field.name] = tags
            continue

        value = posted.get(key, '').strip()

        if not value:
            continue

        if field.type == DetailFieldType.SELECT:
            if value in [code for code, label in field.choices]:
                detail[field.name] = value

        elif field.type == DetailFieldType.INTEGER:
            if value.lstrip('-').isdigit():
                detail[field.name] = int(value)

        elif field.type == DetailFieldType.DECIMAL:
            try:
                detail[field.name] = float(value.replace(',', '.'))
            except ValueError:
                pass

        else:
            detail[field.name] = value

    return detail


def clean_tags(posted_values, choices):
    """
    Valeurs d'un champ à choix multiples : une par pastille, sans vide ni
    doublon. Un texte tapé qui correspond à un libellé proposé est ramené à
    son code, pour que le journal l'affiche comme les autres.
    """

    codes_by_label = {label.lower(): code for code, label in choices}
    tags = []

    for raw in posted_values:
        value = raw.strip()
        value = codes_by_label.get(value.lower(), value)

        if value and value not in tags:
            tags.append(value)

    return tags


def detail_groups(actions, entry=None, presets=None):
    """
    Champs de détail de chaque action, prêts pour le template : (action, [(champ,
    id du champ, valeur)]). Les valeurs viennent de l'entrée modifiée, s'il y en
    a une et que c'est bien son action, sinon des préréglages par code d'action
    (ex. les parasites de l'épisode en cours pour un traitement).

    Pour un champ à choix multiples, la valeur est une liste de (code, libellé).
    """

    presets = presets or {}
    groups = []

    for action in actions:
        if not action.detail_fields:
            continue

        values = presets.get(action.code, {})
        if entry and entry.action_id == action.id and entry.detail:
            values = entry.detail

        fields = []
        for field in action.detail_fields:
            current = values.get(field.name)

            if field.type == DetailFieldType.TAGS and current:
                current = [(code, field.display(code)) for code in current]

            fields.append((field, f'detail_{action.code}_{field.name}', current))

        groups.append((action, fields))

    return groups


def mark_state_changes(history):
    """
    Ajoute à chaque entrée `previous_state` : l'état d'avant, quand l'entrée
    en change. Le journal arrive du plus récent au plus ancien, on le remonte.
    """

    last_state = None

    for entry in reversed(history):
        entry.previous_state = None

        if entry.state:
            if last_state and last_state != entry.state:
                entry.previous_state = last_state
            last_state = entry.state

    return history


@login_required
def detail_plant(request, id_plant: int):


    url = 'Plantes/plants/detail_plant.html'

    plant = get_object_or_404(Plant, id = id_plant, user = request.user)

    # Le formulaire d'ajout au journal est posté sur cette même page
    if request.method == 'POST':
        history_form = PlantHistoryForm(request.POST, request.FILES)

        if history_form.is_valid():
            entry = history_form.save(commit=False)
            entry.plant = plant
            entry.detail = build_detail(entry.action, request.POST) or None
            entry.save()
            plant.refresh_state()

            return redirect('detail_plant', id_plant=plant.id)

    else:
        # Journal ouvert d'office et prérempli depuis l'URL :
        # ?action=CHECK_PESTS pour une inspection, ?state=DEAD pour déclarer la plante morte
        initial = {'date': timezone.localtime()}
        initial['action'] = Action.objects.filter(code=request.GET.get('action', '')).first()
        initial['state'] = PlantState.objects.filter(code=request.GET.get('state', '')).first()

        history_form = PlantHistoryForm(initial=initial)

    open_journal = bool(history_form.errors or history_form.initial.get('action') or history_form.initial.get('state'))

    history = list(PlantHistory.objects
                   .filter(plant=plant)
                   .select_related('action', 'state')
                   .order_by('-date', '-id'))

    # Tous les groupes de champs sont rendus, le JS n'affiche que le bon.
    # Un traitement vise par défaut les parasites de l'épisode en cours
    actions = Action.objects.all().order_by('name')
    presets = {}
    if plant.pest_episode:
        presets['TREAT_PESTS'] = {'pests': plant.pest_episode.pest_codes}

    context = {'plant' : plant, 'history' : mark_state_changes(history), 'history_form' : history_form,
               'detail_groups' : detail_groups(actions, presets=presets), 'open_journal' : open_journal}

    return render(request, url, context)



@login_required
def edit_plant(request, id_plant: int):


    url = 'Plantes/plants/edit_plant.html'

    plant = get_object_or_404(Plant, id = id_plant, user = request.user)

    if request.method == 'POST':
        form = PlantForm(request.POST, request.FILES, instance=plant)
        restrict_to_user(form, request.user)

        if form.is_valid():
            form.save()

            return redirect('detail_plant', id_plant=plant.id)

    else:
        form = PlantForm(instance=plant)
        restrict_to_user(form, request.user)

    context = {'form' : form, 'plant' : plant, 'selected_specie' : selected_specie(form),
               'spot_form' : SpotForm(), 'pot_form' : PotForm()}

    return render(request, url, context)



@login_required
def change_plant_image(request, id_plant: int):
    """
    Remplace la photo d'une plante depuis sa fiche (clic droit sur la planche).
    Ne touche à aucun autre champ.
    """

    plant = get_object_or_404(Plant, id = id_plant, user = request.user)

    if request.method == 'POST':
        form = PlantImageForm(request.POST, request.FILES, instance=plant)

        if form.is_valid():
            form.save()

    return redirect('detail_plant', id_plant=plant.id)



@login_required
def edit_history(request, id_plant: int, id_entry: int):
    """
    Modification d'une entrée du journal, pour corriger une erreur de saisie.
    L'état de la plante est recalculé ensuite : corriger l'entrée suffit.
    """

    url = 'Plantes/plants/edit_history.html'

    plant = get_object_or_404(Plant, id = id_plant, user = request.user)
    entry = get_object_or_404(PlantHistory, id = id_entry, plant = plant)

    if request.method == 'POST':
        form = PlantHistoryForm(request.POST, request.FILES, instance=entry)

        if form.is_valid():
            entry = form.save(commit=False)
            entry.detail = build_detail(entry.action, request.POST) or None
            entry.save()
            plant.refresh_state()

            return redirect(reverse('detail_plant', args=[plant.id]) + '#journal')

    else:
        form = PlantHistoryForm(instance=entry)

    actions = Action.objects.all().order_by('name')

    context = {'plant' : plant, 'entry' : entry, 'history_form' : form,
               'detail_groups' : detail_groups(actions, entry)}

    return render(request, url, context)



@login_required
@require_POST
def delete_history(request, id_plant: int, id_entry: int):
    """Suppression d'une entrée du journal, puis recalcul de l'état de la plante."""

    plant = get_object_or_404(Plant, id = id_plant, user = request.user)
    entry = get_object_or_404(PlantHistory, id = id_entry, plant = plant)

    entry.delete()
    plant.refresh_state()

    return redirect(reverse('detail_plant', args=[plant.id]) + '#journal')
