import json
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from datetime import timedelta
from django.shortcuts import get_object_or_404
from datetime import datetime, timezone
import json
from Plantes.forms import SpecieForm
from Plantes.models import Plant, Specie
from Plantes.utils.species import similar_species


def is_ajax(request):
    """Requête envoyée par la boîte de création rapide du formulaire plante ?"""

    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


SPECIES_PER_PAGE = 50


@login_required
def list_species(request):


    url = 'Plantes/species/list_species.html'

    # Filtre de la barre de recherche : /species/?q=monstera
    query = request.GET.get('q', '').strip()

    species = Specie.objects.all().order_by('vernacular_name')

    if query:
        species = species.filter(
            Q(vernacular_name__icontains=query) | Q(scientific_name__icontains=query)
        )

    page = Paginator(species, SPECIES_PER_PAGE).get_page(request.GET.get('page'))

    context = {'all_species' : page, 'query' : query}

    return render(request, url, context)



@login_required
def detail_specie(request, id_specie: int):


    url = 'Plantes/species/detail_specie.html'

    specie = get_object_or_404(Specie, id = id_specie)

    my_plants = (Plant.objects
                 .filter(specie=specie, user=request.user)
                 .select_related('spot__room')
                 .order_by('surname'))

    context = {'specie' : specie, 'my_plants' : my_plants}

    return render(request, url, context)


SEARCH_LIMIT = 20
SEARCH_MIN_LENGTH = 2


@login_required
def search_species(request):
    """
    Autocomplétion des espèces : /api/species/search/?q=monstera
    Renvoie au plus SEARCH_LIMIT résultats, au format [{id, label}].
    """

    query = request.GET.get('q', '').strip()

    if len(query) < SEARCH_MIN_LENGTH:
        return JsonResponse({'results': []})

    species = Specie.objects.filter(
        Q(vernacular_name__icontains=query) | Q(scientific_name__icontains=query)
    ).order_by('vernacular_name')[:SEARCH_LIMIT]

    results = [{'id': specie.id, 'label': str(specie)} for specie in species]

    return JsonResponse({'results': results})



@login_required
def add_specie(request):
    """
    Création d'une espèce à la main, hors catalogue GBIF (donc sans clé).

    Avant de créer, les noms sont comparés au catalogue : en cas de ressemblance,
    le formulaire revient avec les espèces proches et il faut confirmer
    (champ `confirmed`). Répond en JSON quand l'appel vient de la boîte du
    formulaire plante, en HTML sinon.
    """

    url = 'Plantes/species/add_specie.html'

    similar = []

    if request.method == 'POST':
        form = SpecieForm(request.POST, request.FILES)

        if form.is_valid():
            if not request.POST.get('confirmed'):
                similar = similar_species(form.cleaned_data['vernacular_name'], form.cleaned_data['scientific_name'])

            if similar and is_ajax(request):
                return JsonResponse({'similar': [{'id': specie.id, 'label': str(specie), 'score': score}
                                                 for specie, score in similar]}, status=409)

            if not similar:
                specie = form.save()

                if is_ajax(request):
                    return JsonResponse({'id': specie.id, 'name': str(specie)})

                return redirect('detail_specie', id_specie=specie.id)

        elif is_ajax(request):
            return JsonResponse({'errors': form.errors}, status=400)

    else:
        # Préremplissage depuis une recherche du catalogue sans résultat : /species/add/?name=...
        form = SpecieForm(initial={'vernacular_name': request.GET.get('name', '').strip()})

    context = {'form' : form, 'similar' : similar}

    return render(request, url, context)



@login_required
def edit_specie(request, id_specie: int):
    """
    Modification d'une espèce, importée de GBIF ou non : l'import ne fournit
    aucune exigence de culture, c'est ici qu'on les complète.
    """

    url = 'Plantes/species/edit_specie.html'

    specie = get_object_or_404(Specie, id = id_specie)

    if request.method == 'POST':
        form = SpecieForm(request.POST, request.FILES, instance=specie)

        if form.is_valid():
            form.save()

            return redirect('detail_specie', id_specie=specie.id)

    else:
        form = SpecieForm(instance=specie)

    context = {'form' : form, 'specie' : specie}

    return render(request, url, context)
