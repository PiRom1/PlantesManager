"""
Résumé global de toutes les plantes d'un utilisateur, pour Telegram :
    - Regroupées par emplacement
    - État, dernier arrosage et dernier rempotage de chacune

Le message est au format HTML de Telegram (gras, italique) :

    from Plantes.bot_scripts.plants_summary import summarize_plants
    from Plantes.telegram import TelegramBot
    TelegramBot().send_message(summarize_plants(user), parse_mode='HTML')
"""

from html import escape
from itertools import groupby

from django.db.models import F, Max, Q
from django.utils import timezone

from Plantes.models import Plant, User


NO_SPOT = 'Sans emplacement'

WEEKDAYS = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']



def since(date) -> str:
    """Ancienneté lisible d'une date du journal : « aujourd'hui », « il y a 3 jours », ..."""

    if date is None:
        return 'jamais'

    days = (timezone.localdate() - timezone.localtime(date).date()).days

    if days <= 0:
        return "aujourd'hui"
    if days == 1:
        return 'hier'
    if days < 60:
        return f'il y a {days} jours'
    if days < 730:
        return f'il y a {days // 30} mois'
    return f'il y a {days // 365} ans'



def plant_title(plant: Plant) -> str:
    """Nom en gras (surnom, sinon nom commun), cultivar et nom latin en italique."""

    specie = plant.specie

    if specie is None:
        name = plant.surname or 'Espèce inconnue'
        return f'<b>{escape(name)}</b>'

    name = plant.surname or specie.vernacular_name or specie.scientific_name
    title = f'<b>{escape(name)}</b>'

    if plant.cultivar:
        title += f" ‘{escape(plant.cultivar)}’"

    if specie.scientific_name and specie.scientific_name != name:
        title += f' · <i>{escape(specie.scientific_name)}</i>'

    return title



def summarize_plants(user: User) -> str:

    # Une seule requête : les dernières dates sont calculées par la base.
    # Les actions sont repérées par leur code, stable, pas par leur libellé.
    plants = (Plant.objects
              .filter(user = user)
              .exclude(state__code = 'DEAD')
              .select_related('specie', 'spot', 'state')
              .annotate(last_watering = Max('planthistory__date', filter = Q(planthistory__action__code = 'WATER')),
                        last_repotting = Max('planthistory__date', filter = Q(planthistory__action__code = 'REPOT')))
              .order_by(F('spot__name').asc(nulls_last = True), 'id'))

    today = timezone.localdate()
    summary = f"🌿 <b>Tes plantes</b> - {WEEKDAYS[today.weekday()]} {today:%d/%m}\n"

    if not plants:
        return summary + "\nAucune plante pour l'instant."

    spot_count = len({plant.spot_id for plant in plants if plant.spot_id})
    summary += f"<i>{len(plants)} plante{'s' if len(plants) > 1 else ''}, "
    summary += f"{spot_count} emplacement{'s' if spot_count > 1 else ''}</i>\n"

    for spot_name, spot_plants in groupby(plants, key = lambda plant: plant.spot.name if plant.spot else NO_SPOT):
        summary += f"\n📍 <b>{escape(spot_name.upper())}</b>\n"

        for plant in spot_plants:
            summary += f"\n🪴 {plant_title(plant)}\n"

            if plant.state:
                summary += f"      🌱 {escape(plant.state.name)}\n"

            summary += f"      💧 Arrosage : {since(plant.last_watering)}\n"
            summary += f"      🪣 Rempotage : {since(plant.last_repotting)}\n"

    return summary
