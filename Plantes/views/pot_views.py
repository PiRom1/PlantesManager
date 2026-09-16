from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from Plantes.forms import PotForm
from Plantes.models import Pot


def is_ajax(request):
    """Requête envoyée par la popup de création rapide ?"""

    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


@login_required
def list_pots(request):


    url = 'Plantes/pots/list_pots.html'

    pots = Pot.objects.filter(user=request.user).order_by('denomination')

    context = {'all_pots' : pots}

    return render(request, url, context)



@login_required
def add_pot(request):
    """
    Création d'un pot.

    Répond en JSON quand l'appel vient de la popup du formulaire plante,
    en HTML sinon.
    """

    url = 'Plantes/pots/add_pot.html'

    if request.method == 'POST':
        form = PotForm(request.POST)

        if form.is_valid():
            pot = form.save(commit=False)
            pot.user = request.user
            pot.save()

            if is_ajax(request):
                return JsonResponse({'id': pot.id, 'name': str(pot)})

            return redirect('list_pots')

        if is_ajax(request):
            return JsonResponse({'errors': form.errors}, status=400)

    else:
        form = PotForm()

    context = {'form' : form}

    return render(request, url, context)



@login_required
def detail_pot(request, id_pot: int):
    """Détail et modification d'un pot."""

    url = 'Plantes/pots/detail_pot.html'

    pot = get_object_or_404(Pot, id = id_pot, user = request.user)

    if request.method == 'POST':
        form = PotForm(request.POST, instance=pot)

        if form.is_valid():
            form.save()

            return redirect('list_pots')

    else:
        form = PotForm(instance=pot)

    context = {'form' : form, 'pot' : pot}

    return render(request, url, context)
