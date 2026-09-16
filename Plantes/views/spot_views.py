from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from Plantes.forms import SpotForm
from Plantes.models import Spot


def is_ajax(request):
    """Requête envoyée par la popup de création rapide ?"""

    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


@login_required
def list_spots(request):


    url = 'Plantes/spots/list_spots.html'

    spots = (Spot.objects
             .filter(user=request.user)
             .select_related('exposure', 'humidity')
             .order_by('name'))

    context = {'all_spots' : spots}

    return render(request, url, context)



@login_required
def add_spot(request):
    """
    Création d'un emplacement.

    Répond en JSON quand l'appel vient de la popup du formulaire plante,
    en HTML sinon.
    """

    url = 'Plantes/spots/add_spot.html'

    if request.method == 'POST':
        form = SpotForm(request.POST)

        if form.is_valid():
            spot = form.save(commit=False)
            spot.user = request.user
            spot.save()

            if is_ajax(request):
                return JsonResponse({'id': spot.id, 'name': str(spot)})

            return redirect('list_spots')

        if is_ajax(request):
            return JsonResponse({'errors': form.errors}, status=400)

    else:
        form = SpotForm()

    context = {'form' : form}

    return render(request, url, context)



@login_required
def detail_spot(request, id_spot: int):
    """Détail et modification d'un emplacement."""

    url = 'Plantes/spots/detail_spot.html'

    spot = get_object_or_404(Spot, id = id_spot, user = request.user)

    if request.method == 'POST':
        form = SpotForm(request.POST, instance=spot)

        if form.is_valid():
            form.save()

            return redirect('list_spots')

    else:
        form = SpotForm(instance=spot)

    context = {'form' : form, 'spot' : spot}

    return render(request, url, context)
