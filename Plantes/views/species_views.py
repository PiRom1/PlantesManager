import json
from django.shortcuts import render
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from datetime import timedelta
from django.shortcuts import get_object_or_404
from datetime import datetime, timezone
import json
from Plantes.models import Specie


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
    
    context = {'specie' : specie}

    return render(request, url, context)