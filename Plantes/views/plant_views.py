from datetime import datetime, time

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from Plantes.forms import PlantForm, PlantHistoryForm, PlantImageForm, PotForm, SpotForm
from Plantes.models import Action, DetailFieldType, Plant, PlantHistory, Pot, Specie, Spot


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

    plants = (Plant.objects
              .filter(user=request.user)
              .select_related('specie', 'state', 'spot', 'pot', 'substrate')
              .order_by('specie__vernacular_name'))

    context = {'all_plants' : plants}

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


def detail_groups(actions, entry=None):
    """
    Champs de détail de chaque action, prêts pour le template : (action, [(champ,
    id du champ, valeur)]). Les valeurs viennent de l'entrée modifiée, s'il y en
    a une et que c'est bien son action.
    """

    groups = []

    for action in actions:
        if not action.detail_fields:
            continue

        values = {}
        if entry and entry.action_id == action.id and entry.detail:
            values = entry.detail

        fields = [(field, f'detail_{action.code}_{field.name}', values.get(field.name))
                  for field in action.detail_fields]
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
        history_form = PlantHistoryForm(initial={'date': timezone.localtime()})

    history = list(PlantHistory.objects
                   .filter(plant=plant)
                   .select_related('action', 'state')
                   .order_by('-date', '-id'))

    # Tous les groupes de champs sont rendus, le JS n'affiche que le bon
    actions = Action.objects.all().order_by('name')

    context = {'plant' : plant, 'history' : mark_state_changes(history), 'history_form' : history_form,
               'detail_groups' : detail_groups(actions)}

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
