from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from Plantes.forms import PlantForm, PlantHistoryForm, PotForm, SpotForm
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

            return redirect('detail_plant', id_plant=plant.id)

    else:
        history_form = PlantHistoryForm(initial={'date': timezone.localtime()})

    history = (PlantHistory.objects
               .filter(plant=plant)
               .select_related('action')
               .order_by('-date'))

    # Tous les groupes de champs sont rendus, le JS n'affiche que le bon
    actions = Action.objects.all().order_by('name')

    context = {'plant' : plant, 'history' : history, 'history_form' : history_form,
               'actions' : actions}

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
