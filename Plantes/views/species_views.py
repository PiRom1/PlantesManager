import json
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from datetime import timedelta
from django.shortcuts import get_object_or_404
from datetime import datetime, timezone
import json
from Plantes.models import Plant, Specie


SPECIES_PER_PAGE = 50


@login_required
def list_species(request):


    url = 'Plantes/species/list_species.html'

    species = Specie.objects.all().order_by('vernacular_name')
    page = Paginator(species, SPECIES_PER_PAGE).get_page(request.GET.get('page'))

    context = {'all_species' : page}

    return render(request, url, context)



@login_required
def detail_specie(request, id_specie: int):


    url = 'Plantes/species/detail_specie.html'

    specie = get_object_or_404(Specie, id = id_specie)

    my_plants = (Plant.objects
                 .filter(specie=specie, user=request.user)
                 .select_related('spot')
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
