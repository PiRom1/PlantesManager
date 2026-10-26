from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from Plantes.forms import RoomForm
from Plantes.models import Room


def is_ajax(request):
    """Requête envoyée par la popup de création rapide ?"""

    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


@login_required
def list_rooms(request):


    url = 'Plantes/rooms/list_rooms.html'

    rooms = (Room.objects
             .filter(user=request.user)
             .annotate(spot_count=Count('spot', distinct=True), plant_count=Count('spot__plant', distinct=True))
             .order_by('name'))

    context = {'all_rooms' : rooms}

    return render(request, url, context)



@login_required
def add_room(request):
    """
    Création d'une pièce.

    Répond en JSON quand l'appel vient de la popup du formulaire emplacement,
    en HTML sinon.
    """

    url = 'Plantes/rooms/add_room.html'

    if request.method == 'POST':
        form = RoomForm(request.POST)

        if form.is_valid():
            room = form.save(commit=False)
            room.user = request.user
            room.save()

            if is_ajax(request):
                return JsonResponse({'id': room.id, 'name': str(room)})

            return redirect('list_rooms')

        if is_ajax(request):
            return JsonResponse({'errors': form.errors}, status=400)

    else:
        form = RoomForm()

    context = {'form' : form}

    return render(request, url, context)



@login_required
def detail_room(request, id_room: int):
    """Détail et modification d'une pièce."""

    url = 'Plantes/rooms/detail_room.html'

    room = get_object_or_404(Room, id = id_room, user = request.user)

    if request.method == 'POST':
        form = RoomForm(request.POST, instance=room)

        if form.is_valid():
            form.save()

            return redirect('list_rooms')

    else:
        form = RoomForm(instance=room)

    spots = room.spot_set.select_related('exposure', 'humidity').order_by('name')

    context = {'form' : form, 'room' : room, 'spots' : spots}

    return render(request, url, context)



@login_required
@require_POST
def delete_room(request, id_room: int):
    """Suppression d'une pièce : ses emplacements restent, sans pièce (SET_NULL)."""

    room = get_object_or_404(Room, id = id_room, user = request.user)

    room.delete()

    return redirect('list_rooms')
