from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.http import QueryDict
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from Plantes.forms import CareForm, CareOverrideForm
from Plantes.models import Action, Plant, PlantHistory
from Plantes.views.plant_views import build_detail, detail_groups


# Préfixe des champs du gabarit de précisions, remplacé par p<id> côté navigateur
TEMPLATE_PREFIX = 'p__'


def living_plants(user):
    """Plantes de l'utilisateur à entretenir, dans l'ordre pièce, emplacement, nom. Les mortes n'en sont plus."""

    return (Plant.objects
            .filter(user=user)
            .exclude(state__code='DEAD')
            .select_related('specie', 'state', 'spot__room')
            .order_by(F('spot__room__name').asc(nulls_last=True), F('spot__name').asc(nulls_last=True),
                      'spot_id', 'surname', 'specie__vernacular_name'))


def grouped_by_spot(plants):
    """[(emplacement ou None, [plantes])], dans l'ordre reçu ; les sans emplacement en dernier."""

    groups = []

    for plant in plants:
        if not groups or groups[-1][0] != plant.spot:
            groups.append((plant.spot, []))

        groups[-1][1].append(plant)

    return groups


def unprefixed(posted, prefix):
    """Les champs « p12-xxx » du POST sous le nom « xxx », tels que build_detail les attend."""

    data = QueryDict(mutable=True)

    for key in posted:
        if key.startswith(prefix + '-'):
            data.setlist(key[len(prefix) + 1:], posted.getlist(key))

    return data


def build_entries(form, chosen, request):
    """
    Une entrée de journal par plante cochée, non enregistrée. Une plante dont
    les précisions ont été ouvertes (champ p<id>-refined) a ses propres
    options et son propre commentaire, préremplis du commun puis modifiés ;
    les autres prennent le commun. Renvoie (entrées, erreurs).
    """

    action = form.cleaned_data['action']
    common = build_detail(action, request.POST)
    entries, errors = [], []

    for plant in chosen:
        prefix = f'p{plant.id}'
        override = CareOverrideForm(request.POST, request.FILES, prefix=prefix)

        if not override.is_valid():
            errors.append(f'{plant} : précisions invalides ({", ".join(override.errors)}).')
            continue

        own = override.cleaned_data
        refined = f'{prefix}-refined' in request.POST

        entries.append(PlantHistory(
            plant=plant, action=action, date=form.cleaned_data['date'],
            state=own['state'], image=own['image'],
            comment=(own['comment'] if refined else form.cleaned_data['comment']) or None,
            height=own['height'], width=own['width'], n_leaves=own['n_leaves'],
            detail=(build_detail(action, unprefixed(request.POST, prefix)) if refined else common) or None,
        ))

    return entries, errors


@login_required
def care(request):
    """
    Entretien groupé : une action et ses options, un commentaire, puis les
    plantes cochées, par emplacement. Chaque plante peut préciser ce qui la
    distingue du lot (options et commentaire préremplis du commun, état,
    mesures, photo). Une entrée de journal par plante à l'enregistrement.
    """

    url = 'Plantes/care/care.html'

    plants = living_plants(request.user)
    errors = []
    checked = []

    if request.method == 'POST':
        form = CareForm(request.POST)
        checked = [int(value) for value in request.POST.getlist('plants') if value.isdigit()]
        chosen = [plant for plant in plants if plant.id in checked]

        if not chosen:
            errors.append('Coche au moins une plante.')

        if form.is_valid() and not errors:
            entries, errors = build_entries(form, chosen, request)

            if not errors:
                with transaction.atomic():
                    for entry in entries:
                        entry.save()
                        if entry.state:
                            entry.plant.refresh_state()

                return redirect(reverse('care') + f'?saved={len(entries)}')

    else:
        form = CareForm(initial={'date': timezone.localtime()})

    actions = Action.objects.all().order_by('name')
    saved = request.GET.get('saved', '')

    context = {'form' : form, 'errors' : errors, 'groups' : grouped_by_spot(plants), 'total' : len(plants),
               'checked' : checked, 'detail_groups' : detail_groups(actions),
               'override_groups' : detail_groups(actions, prefix=f'{TEMPLATE_PREFIX}-'),
               'override_form' : CareOverrideForm(prefix=TEMPLATE_PREFIX),
               'saved' : int(saved) if saved.isdigit() else None}

    return render(request, url, context)
