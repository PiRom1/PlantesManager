"""
Tests de la logique qui ne se voit pas dans un template : déduction de
l'épisode parasitaire, lecture des champs à choix multiples, reprise des
anciennes inspections par la migration, équipement cumulé.

    python manage.py test Plantes
"""

from datetime import timedelta

from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from Plantes.models import Action, Plant, PlantHistory, PlantState, Specie, Spot, User
from Plantes.views.plant_views import build_detail, clean_tags


def make_user(username='romain'):
    return User.objects.create_user(f'{username}@example.org', password='secret', username=username)


class PestEpisodeTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.check = Action.objects.create(code='CHECK_PESTS', name='Inspection parasites', description='')
        self.treat = Action.objects.create(code='TREAT_PESTS', name='Traitement parasites', description='')
        self.specie = Specie.objects.create(vernacular_name='Monstera', scientific_name='Monstera deliciosa')
        self.plant = Plant.objects.create(user=self.user, specie=self.specie)
        self.day = timezone.now() - timedelta(days=30)

    def entry(self, action, days, **detail):
        return PlantHistory.objects.create(plant=self.plant, action=action,
                                           date=self.day + timedelta(days=days), detail=detail or None)

    def episode(self):
        # cached_property : on relit la plante pour repartir du journal
        return Plant.objects.get(pk=self.plant.pk).pest_episode

    def test_sans_inspection_pas_d_episode(self):
        self.assertIsNone(self.episode())

    def test_inspection_positive_ouvre_un_episode(self):
        self.entry(self.check, 1, result='SUSPICION', pests=['THRIPS'])
        episode = self.episode()

        self.assertIsNotNone(episode)
        self.assertFalse(episode.confirmed)
        self.assertEqual(episode.result_label, 'Suspicion')
        self.assertEqual(episode.pests, 'Thrips')

    def test_absence_referme_l_episode(self):
        self.entry(self.check, 1, result='CONFIRMED', pests=['THRIPS'])
        self.entry(self.check, 5, result='CLEAR')

        self.assertIsNone(self.episode())

    def test_un_traitement_ne_referme_pas_l_episode(self):
        self.entry(self.check, 1, result='CONFIRMED', pests=['THRIPS'], severity='LIGHT')
        self.entry(self.treat, 2, pests=['THRIPS'], treatment=['NEEM', 'Produit maison'], dose='5 mL/L')
        self.entry(self.treat, 9, pests=['THRIPS'], treatment=['MANUAL'])
        episode = self.episode()

        self.assertIsNotNone(episode)
        self.assertTrue(episode.confirmed)
        self.assertEqual(episode.severity, 'Légère')
        self.assertEqual(len(episode.treatments), 2)

        # Du plus récent au plus ancien, libellés traduits, texte libre conservé
        lines = episode.treatment_lines
        self.assertEqual(lines[0][1], 'Retrait manuel')
        self.assertEqual(lines[1][1], 'Huile de neem, Produit maison')
        self.assertEqual(lines[1][2], '5 mL/L')

    def test_les_traitements_d_avant_l_episode_ne_comptent_pas(self):
        self.entry(self.check, 1, result='CONFIRMED', pests=['APHID'])
        self.entry(self.treat, 2, treatment=['BLACK_SOAP'])
        self.entry(self.check, 3, result='CLEAR')
        self.entry(self.check, 10, result='SUSPICION', pests=['SCALE'])
        episode = self.episode()

        self.assertEqual(episode.treatments, [])
        self.assertEqual(episode.since.date(), (self.day + timedelta(days=10)).date())

    def test_parasites_cumules_sur_l_episode_les_plus_recents_d_abord(self):
        self.entry(self.check, 1, result='SUSPICION', pests=['THRIPS'])
        self.entry(self.check, 4, result='CONFIRMED', pests=['MEALYBUG', 'Acariens inconnus'])
        episode = self.episode()

        self.assertEqual(episode.pest_codes, ['MEALYBUG', 'Acariens inconnus', 'THRIPS'])
        self.assertEqual(episode.pests, 'Cochenille farineuse, Acariens inconnus, Thrips')

    def test_inspection_sans_resultat_est_ignoree(self):
        self.entry(self.check, 1, result='CONFIRMED', pests=['THRIPS'])
        self.entry(self.check, 2)

        self.assertIsNotNone(self.episode())


class TagsFieldTests(TestCase):

    def setUp(self):
        self.check = Action.objects.create(code='CHECK_PESTS', name='Inspection parasites', description='')

    def test_clean_tags_ramene_les_libelles_a_leur_code_et_dedoublonne(self):
        choices = Action.detail_field('CHECK_PESTS', 'pests').choices
        tags = clean_tags(['THRIPS', ' thrips ', 'Pucerons', '', 'Acariens', 'Acariens'], choices)

        self.assertEqual(tags, ['THRIPS', 'APHID', 'Acariens'])

    def test_build_detail_lit_la_liste_postee(self):
        posted = QueryDict(mutable=True)
        posted.update({'detail_CHECK_PESTS_result': 'CONFIRMED', 'detail_CHECK_PESTS_severity': 'SEVERE'})
        posted.setlist('detail_CHECK_PESTS_pests', ['THRIPS', 'Truc'])

        detail = build_detail(self.check, posted)

        self.assertEqual(detail, {'result': 'CONFIRMED', 'pests': ['THRIPS', 'Truc'], 'severity': 'SEVERE'})

    def test_build_detail_sans_tag_n_ecrit_pas_la_cle(self):
        posted = QueryDict('detail_CHECK_PESTS_result=CLEAR')

        self.assertEqual(build_detail(self.check, posted), {'result': 'CLEAR'})

    def test_resume_du_journal_traduit_les_codes(self):
        plant = Plant.objects.create(user=make_user())
        entry = PlantHistory.objects.create(plant=plant, action=self.check, date=timezone.now(),
                                            detail={'result': 'CONFIRMED', 'pests': ['THRIPS', 'Acariens']})

        self.assertEqual(entry.detail_summary, [('Résultat', 'Présence'), ('Parasites', 'Thrips, Acariens')])


class PestCheckMigrationTests(TestCase):

    def test_les_anciennes_inspections_sont_converties(self):
        from importlib import import_module
        from django.apps import apps

        convert = import_module('Plantes.migrations.0007_plant_equipment_pest_journal').convert_pest_checks

        check = Action.objects.create(code='CHECK_PESTS', name='Inspection parasites', description='')
        water = Action.objects.create(code='WATER', name='Arrosage', description='')
        plant = Plant.objects.create(user=make_user())

        old = PlantHistory.objects.create(plant=plant, action=check, date=timezone.now(), comment='Sous les feuilles',
                                          detail={'result': 'CONFIRMED', 'pest': 'THRIPS', 'severity': 'LIGHT', 'treatment': 'NEEM'})
        other = PlantHistory.objects.create(plant=plant, action=check, date=timezone.now(),
                                            detail={'result': 'SUSPICION', 'pest': 'OTHER', 'treatment': 'NONE'})
        untouched = PlantHistory.objects.create(plant=plant, action=water, date=timezone.now(),
                                                detail={'volume_ml': 200})
        already = PlantHistory.objects.create(plant=plant, action=check, date=timezone.now(),
                                              detail={'result': 'CLEAR'})

        convert(apps, None)

        old.refresh_from_db()
        self.assertEqual(old.detail, {'result': 'CONFIRMED', 'pests': ['THRIPS'], 'severity': 'LIGHT'})
        self.assertEqual(old.comment, 'Sous les feuilles\nTraitement : Huile de neem')

        other.refresh_from_db()
        self.assertEqual(other.detail, {'result': 'SUSPICION', 'pests': ['Autre']})
        self.assertIsNone(other.comment)

        untouched.refresh_from_db()
        self.assertEqual(untouched.detail, {'volume_ml': 200})

        already.refresh_from_db()
        self.assertEqual(already.detail, {'result': 'CLEAR'})


class EquipmentTests(TestCase):

    def test_equipement_cumule_plante_et_emplacement(self):
        user = make_user()
        spot = Spot.objects.create(user=user, name='Salon', has_heater=True, has_additional_light=True)
        plant = Plant.objects.create(user=user, spot=spot, has_additional_light=True, has_moister=True)

        self.assertEqual(plant.equipment, [
            ("Éclairage d'appoint", 'plante et emplacement'),
            ('Chauffage', 'emplacement'),
            ('Humidificateur', 'plante'),
        ])

    def test_sans_emplacement_ni_equipement(self):
        plant = Plant.objects.create(user=make_user())

        self.assertEqual(plant.equipment, [])


class PlantPagesTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.check = Action.objects.create(code='CHECK_PESTS', name='Inspection parasites', description='')
        self.treat = Action.objects.create(code='TREAT_PESTS', name='Traitement parasites', description='')
        self.dead = PlantState.objects.create(code='DEAD', name='Morte', description='')
        self.plant = Plant.objects.create(user=self.user, surname='Momo')

    def test_fiche_sans_episode(self):
        response = self.client.get(reverse('detail_plant', args=[self.plant.id]))

        self.assertContains(response, 'Aucun parasite constaté')
        self.assertNotContains(response, 'data-open-on-load')

    def test_fiche_avec_episode_et_traitement_prerempli(self):
        PlantHistory.objects.create(plant=self.plant, action=self.check, date=timezone.now(),
                                    detail={'result': 'CONFIRMED', 'pests': ['THRIPS'], 'severity': 'MODERATE'})

        response = self.client.get(reverse('detail_plant', args=[self.plant.id]))

        self.assertContains(response, 'pests--confirmed')
        self.assertContains(response, 'Modérée')
        # Le traitement vise par défaut les parasites de l'épisode
        self.assertContains(response, 'name="detail_TREAT_PESTS_pests" value="THRIPS"')

    def test_journal_ouvert_et_prerempli_depuis_l_url(self):
        response = self.client.get(reverse('detail_plant', args=[self.plant.id]) + '?state=DEAD')

        self.assertContains(response, 'data-open-on-load')
        self.assertContains(response, 'data-focus="id_comment"')
        self.assertContains(response, f'<option value="{self.dead.id}" selected>Morte</option>', html=False)

    def test_poster_une_inspection_avec_plusieurs_parasites(self):
        response = self.client.post(reverse('detail_plant', args=[self.plant.id]), {
            'action': self.check.id,
            'date': '2026-10-14T10:00',
            'detail_CHECK_PESTS_result': 'SUSPICION',
            'detail_CHECK_PESTS_pests': ['THRIPS', 'Bestiole blanche'],
        })

        self.assertRedirects(response, reverse('detail_plant', args=[self.plant.id]))
        entry = PlantHistory.objects.get()
        self.assertEqual(entry.detail, {'result': 'SUSPICION', 'pests': ['THRIPS', 'Bestiole blanche']})

        response = self.client.get(reverse('edit_history', args=[self.plant.id, entry.id]))
        self.assertContains(response, 'Bestiole blanche')
        self.assertContains(response, 'name="detail_CHECK_PESTS_pests" value="THRIPS"')

    def test_filtre_parasitees(self):
        clean = Plant.objects.create(user=self.user, surname='Saine')
        PlantHistory.objects.create(plant=self.plant, action=self.check, date=timezone.now(),
                                    detail={'result': 'SUSPICION'})

        response = self.client.get(reverse('list_plants'))
        self.assertContains(response, 'Parasitées (1)')
        self.assertContains(response, 'Saine')
        self.assertContains(response, 'Parasites ?')

        response = self.client.get(reverse('list_plants') + '?filter=pests')
        self.assertContains(response, 'Momo')
        self.assertNotContains(response, 'Saine')


class CuttingTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.propagate = Action.objects.create(code='PROPAGATE', name='Bouturage', description='')
        self.cutting_state = PlantState.objects.create(code='CUTTING', name='Bouture', description='')
        self.specie = Specie.objects.create(vernacular_name='Monstera', scientific_name='Monstera deliciosa')
        self.mother = Plant.objects.create(user=self.user, specie=self.specie, cultivar='Variegata', surname='Maman')

    def test_formulaire_prerempli_depuis_la_mere(self):
        response = self.client.get(reverse('add_cutting', args=[self.mother.id]))

        self.assertContains(response, 'Déclarer une bouture')
        self.assertContains(response, f'<input type="hidden" name="specie" value="{self.specie.id}"', html=False)
        self.assertContains(response, 'value="Variegata"')
        self.assertContains(response, f'<option value="{self.mother.id}" selected>Maman</option>', html=False)
        self.assertContains(response, f'<option value="{self.cutting_state.id}" selected>Bouture</option>', html=False)
        self.assertContains(response, 'value="Bouture de Maman"')
        self.assertContains(response, 'name="method"')
        # Date du jour au format ISO, le seul que le champ date du navigateur accepte
        self.assertContains(response, f'name="acquisition_date" value="{timezone.localdate():%Y-%m-%d}"')

    def test_declarer_une_bouture_cree_la_plante_et_l_entree_chez_la_mere(self):
        response = self.client.post(reverse('add_cutting', args=[self.mother.id]), {
            'specie': self.specie.id,
            'cultivar': 'Variegata',
            'surname': 'Bébé',
            'state': self.cutting_state.id,
            'father': self.mother.id,
            'acquisition_date': '2026-10-14',
            'origin': 'Bouture de Maman',
            'method': 'STEM_CUTTING',
            'medium': 'WATER',
            'hormone': 'on',
        })

        cutting = Plant.objects.get(surname='Bébé')
        self.assertRedirects(response, reverse('detail_plant', args=[cutting.id]))
        self.assertEqual(cutting.father, self.mother)
        self.assertEqual(cutting.state, self.cutting_state)

        # Arrivée chez la bouture, bouturage chez la mère, à la même date
        arrival = PlantHistory.objects.get(plant=cutting)
        propagation = PlantHistory.objects.get(plant=self.mother)
        self.assertEqual(propagation.action, self.propagate)
        self.assertEqual(propagation.detail, {'n_cuttings': 1, 'hormone': True, 'method': 'STEM_CUTTING', 'medium': 'WATER'})
        self.assertEqual(propagation.comment, 'Bouture : Bébé')
        self.assertEqual(propagation.date, arrival.date)

    def test_bouturage_sans_detail(self):
        self.client.post(reverse('add_cutting', args=[self.mother.id]), {
            'specie': self.specie.id, 'father': self.mother.id,
        })

        propagation = PlantHistory.objects.get(plant=self.mother)
        self.assertEqual(propagation.detail, {'n_cuttings': 1, 'hormone': False})

    def test_la_mere_doit_etre_a_moi(self):
        other = Plant.objects.create(user=make_user('autre'))

        self.assertEqual(self.client.get(reverse('add_cutting', args=[other.id])).status_code, 404)
