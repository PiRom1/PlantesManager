"""
Tests de la logique qui ne se voit pas dans un template : déduction de
l'épisode parasitaire, lecture des champs à choix multiples, reprise des
anciennes inspections par la migration, équipement cumulé.

    python manage.py test Plantes
"""

import os
from datetime import timedelta

from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from Plantes.models import Action, Plant, PlantHistory, PlantState, Pot, Room, Specie, Spot, User
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

    def test_absence_ignore_parasites_et_gravite(self):
        # Champs masqués dans le formulaire : même postés, ils ne comptent pas
        posted = QueryDict('detail_CHECK_PESTS_result=CLEAR&detail_CHECK_PESTS_pests=THRIPS&detail_CHECK_PESTS_severity=SEVERE')

        self.assertEqual(build_detail(self.check, posted), {'result': 'CLEAR'})

    def test_les_champs_conditionnels_portent_leur_condition_dans_le_formulaire(self):
        self.client.force_login(make_user())
        plant = Plant.objects.create(user=User.objects.get())

        response = self.client.get(reverse('detail_plant', args=[plant.id]))

        self.assertContains(response, 'data-shown-when="detail_CHECK_PESTS_result" data-shown-values="SUSPICION CONFIRMED"', count=2)

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
        self.assertContains(response, 'specimen__pest--suspicion" title="Parasite suspecté"')
        self.assertNotContains(response, 'specimen__pest--confirmed')

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
        self.assertContains(response, f'<option value="{self.mother.id}" selected>Maman · Monstera</option>', html=False)
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


class DeleteTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.spot = Spot.objects.create(user=self.user, name='Salon')
        self.pot = Pot.objects.create(user=self.user, denomination='Terre cuite 12')
        self.plant = Plant.objects.create(user=self.user, surname='Momo', spot=self.spot, pot=self.pot)

    def test_supprimer_un_emplacement_laisse_les_plantes_sans_emplacement(self):
        response = self.client.get(reverse('detail_spot', args=[self.spot.id]))
        self.assertContains(response, '1 plante y est rattachée : elle restera dans ta collection, sans emplacement.')

        response = self.client.post(reverse('delete_spot', args=[self.spot.id]))

        self.assertRedirects(response, reverse('list_spots'))
        self.assertFalse(Spot.objects.filter(id=self.spot.id).exists())
        self.plant.refresh_from_db()
        self.assertIsNone(self.plant.spot)

    def test_supprimer_un_pot_laisse_les_plantes_sans_pot(self):
        Plant.objects.create(user=self.user, pot=self.pot)
        response = self.client.get(reverse('detail_pot', args=[self.pot.id]))
        self.assertContains(response, '2 plantes y sont installées : elles resteront dans ta collection, sans pot.')

        response = self.client.post(reverse('delete_pot', args=[self.pot.id]))

        self.assertRedirects(response, reverse('list_pots'))
        self.plant.refresh_from_db()
        self.assertIsNone(self.plant.pot)

    def test_supprimer_une_plante_emporte_son_journal_et_ses_photos(self):
        import tempfile
        from django.test import override_settings

        PlantHistory.objects.create(plant=self.plant, date=timezone.now(), comment='Arrivée')
        cutting = Plant.objects.create(user=self.user, father=self.plant)

        with tempfile.TemporaryDirectory() as media_root:
            folder = os.path.join(media_root, 'PlantImages', str(self.plant.id))
            os.makedirs(folder)
            open(os.path.join(folder, 'photo.jpg'), 'w').close()

            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.get(reverse('detail_plant', args=[self.plant.id]))
                self.assertContains(response, 'Supprimer Momo ?')
                self.assertContains(response, 'Sa bouture restera dans ta collection, sans plante mère.')
                self.assertContains(response, 'href="?state=DEAD"')

                response = self.client.post(reverse('delete_plant', args=[self.plant.id]))

            self.assertRedirects(response, reverse('list_plants'))
            self.assertFalse(Plant.objects.filter(id=self.plant.id).exists())
            self.assertFalse(PlantHistory.objects.exists())
            self.assertFalse(os.path.exists(folder))

        cutting.refresh_from_db()
        self.assertIsNone(cutting.father)

    def test_suppression_en_post_seulement_et_chez_soi(self):
        self.assertEqual(self.client.get(reverse('delete_plant', args=[self.plant.id])).status_code, 405)

        other = Plant.objects.create(user=make_user('autre'))
        self.assertEqual(self.client.post(reverse('delete_plant', args=[other.id])).status_code, 404)
        self.assertTrue(Plant.objects.filter(id=other.id).exists())


class RoomTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.room = Room.objects.create(user=self.user, name='Salon')
        self.spot = Spot.objects.create(user=self.user, name='Étagère', room=self.room)
        self.specie = Specie.objects.create(vernacular_name='Monstera', scientific_name='Monstera deliciosa')
        self.plant = Plant.objects.create(user=self.user, specie=self.specie, spot=self.spot)

    def test_supprimer_une_piece_laisse_les_emplacements_sans_piece(self):
        response = self.client.get(reverse('detail_room', args=[self.room.id]))
        self.assertContains(response, "1 emplacement s'y trouve")

        response = self.client.post(reverse('delete_room', args=[self.room.id]))
        self.spot.refresh_from_db()

        self.assertRedirects(response, reverse('list_rooms'))
        self.assertFalse(Room.objects.filter(id=self.room.id).exists())
        self.assertIsNone(self.spot.room)
        self.assertEqual(self.plant.spot, self.spot)

    def test_la_piece_s_affiche_devant_l_emplacement(self):
        response = self.client.get(reverse('detail_plant', args=[self.plant.id]))
        self.assertContains(response, 'Salon</a> · <a href="%s">Étagère' % reverse('detail_spot', args=[self.spot.id]))

        response = self.client.get(reverse('list_plants'))
        self.assertContains(response, '<span class="specimen__tag">Salon · Étagère</span>')

    def test_le_menu_des_pieces_ne_propose_que_les_miennes(self):
        Room.objects.create(user=make_user('autre'), name='Chambre des autres')

        response = self.client.get(reverse('add_spot'))
        self.assertContains(response, 'Salon')
        self.assertNotContains(response, 'Chambre des autres')

        # Même chose dans la popup emplacement du formulaire plante
        response = self.client.get(reverse('add_plant'))
        self.assertContains(response, 'Salon')
        self.assertNotContains(response, 'Chambre des autres')

    def test_creation_a_la_volee_en_json(self):
        response = self.client.post(reverse('add_room'), {'name': 'Véranda'}, headers={'X-Requested-With': 'XMLHttpRequest'})

        self.assertEqual(response.status_code, 200)
        room = Room.objects.get(name='Véranda')
        self.assertEqual(room.user, self.user)
        self.assertEqual(response.json(), {'id': room.id, 'name': 'Véranda'})

    def test_les_pieces_des_autres_sont_introuvables(self):
        other = Room.objects.create(user=make_user('autre'), name='Chambre')

        self.assertEqual(self.client.get(reverse('detail_room', args=[other.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse('delete_room', args=[other.id])).status_code, 404)


class PlantListFiltersTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.salon = Room.objects.create(user=self.user, name='Salon')
        self.chambre = Room.objects.create(user=self.user, name='Chambre')
        self.etagere = Spot.objects.create(user=self.user, name='Etagère', room=self.salon)
        self.vitrine = Spot.objects.create(user=self.user, name='Vitrine', room=self.salon)
        self.bureau = Spot.objects.create(user=self.user, name='Bureau', room=self.chambre)
        monstera = Specie.objects.create(vernacular_name='Monstera', scientific_name='Monstera deliciosa')
        pilea = Specie.objects.create(vernacular_name='Pilea', scientific_name='Pilea peperomioides')
        self.momo = Plant.objects.create(user=self.user, specie=monstera, surname='Momo', spot=self.etagere)
        self.pipi = Plant.objects.create(user=self.user, specie=pilea, surname='Pipi', spot=self.vitrine)
        self.anon = Plant.objects.create(user=self.user, specie=monstera, spot=self.bureau)

    def names(self, response):
        return [plant.id for plant in response.context['all_plants']]

    def test_sans_filtre_tout_le_monde_trie_par_espece(self):
        response = self.client.get(reverse('list_plants'))
        self.assertEqual(self.names(response), [self.anon.id, self.momo.id, self.pipi.id])
        self.assertContains(response, '3 plantes dans ta collection')

    def test_recherche_sur_surnom_et_espece(self):
        self.assertEqual(self.names(self.client.get(reverse('list_plants'), {'q': 'momo'})), [self.momo.id])
        self.assertEqual(self.names(self.client.get(reverse('list_plants'), {'q': 'deliciosa'})), [self.anon.id, self.momo.id])

    def test_filtre_par_piece_puis_emplacement(self):
        response = self.client.get(reverse('list_plants'), {'room': self.salon.id})
        self.assertEqual(self.names(response), [self.momo.id, self.pipi.id])
        self.assertContains(response, '2 plantes sur 3')
        # Le menu des emplacements ne propose que ceux de la pièce
        self.assertEqual([spot.id for spot in response.context['spots']], [self.etagere.id, self.vitrine.id])

        response = self.client.get(reverse('list_plants'), {'room': self.salon.id, 'spot': self.vitrine.id})
        self.assertEqual(self.names(response), [self.pipi.id])

    def test_emplacement_hors_de_la_piece_ignore(self):
        response = self.client.get(reverse('list_plants'), {'room': self.salon.id, 'spot': self.bureau.id})
        self.assertEqual(self.names(response), [self.momo.id, self.pipi.id])
        self.assertIsNone(response.context['spot_id'])

    def test_tri_par_surnom_les_sans_surnom_a_la_fin(self):
        response = self.client.get(reverse('list_plants'), {'sort': 'surname'})
        self.assertEqual(self.names(response), [self.momo.id, self.pipi.id, self.anon.id])

    def test_tri_par_piece_et_emplacement(self):
        response = self.client.get(reverse('list_plants'), {'sort': 'place'})
        self.assertEqual(self.names(response), [self.anon.id, self.momo.id, self.pipi.id])

    def test_parametres_invalides_ignores(self):
        response = self.client.get(reverse('list_plants'), {'room': 'abc', 'sort': 'nimporte'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.names(response)), 3)

    def test_aucun_resultat(self):
        response = self.client.get(reverse('list_plants'), {'q': 'cactus'})
        self.assertContains(response, 'Aucune plante ne correspond')

    def test_le_filtre_parasitees_garde_les_autres_filtres(self):
        response = self.client.get(reverse('list_plants'), {'room': self.salon.id})
        self.assertContains(response, f'href="?room={self.salon.id}&amp;filter=pests"')


class SpecieNotesTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.specie = Specie.objects.create(vernacular_name='Monstera', scientific_name='Monstera deliciosa',
                                            abiotic_conditions='Lumière vive sans soleil direct.\nCraint les courants d\'air.')
        self.plant = Plant.objects.create(user=self.user, specie=self.specie)

    def test_les_notes_de_l_espece_se_lisent_sur_la_plante(self):
        response = self.client.get(reverse('detail_plant', args=[self.plant.id]))

        self.assertContains(response, 'Lumière vive sans soleil direct.<br>Craint les courants d&#x27;air.')
        self.assertContains(response, reverse('edit_specie', args=[self.specie.id]))

    def test_sans_notes_la_plante_invite_a_en_ajouter(self):
        self.specie.abiotic_conditions = None
        self.specie.save()

        response = self.client.get(reverse('detail_plant', args=[self.plant.id]))
        self.assertContains(response, "Rien de noté encore sur l'espèce.")

    def test_les_notes_se_modifient_sur_la_fiche_espece(self):
        response = self.client.post(reverse('edit_specie', args=[self.specie.id]), {
            'vernacular_name': 'Monstera',
            'scientific_name': 'Monstera deliciosa',
            'abiotic_conditions': 'Substrat drainant.',
        })
        self.specie.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.specie.abiotic_conditions, 'Substrat drainant.')
        self.assertContains(self.client.get(reverse('detail_specie', args=[self.specie.id])), 'Substrat drainant.')


class MotherChoiceLabelTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.specie = Specie.objects.create(vernacular_name='Monstera', scientific_name='Monstera deliciosa')

    def test_surnom_et_nom_commun(self):
        plant = Plant.objects.create(user=self.user, specie=self.specie, surname='Momo')
        self.assertEqual(plant.choice_label, 'Momo · Monstera')

    def test_sans_surnom_le_libelle_courant_contient_deja_l_espece(self):
        plant = Plant.objects.create(user=self.user, specie=self.specie)
        self.assertEqual(plant.choice_label, f'Monstera (Monstera deliciosa) #{plant.id}')

    def test_sans_espece_le_surnom_seul(self):
        plant = Plant.objects.create(user=self.user, surname='Momo')
        self.assertEqual(plant.choice_label, 'Momo')

    def test_le_menu_plante_mere_affiche_l_espece(self):
        plant = Plant.objects.create(user=self.user, specie=self.specie, surname='Momo')
        Plant.objects.create(user=make_user('autre'), specie=self.specie, surname='Pas à moi')

        response = self.client.get(reverse('add_plant'))

        self.assertContains(response, f'<option value="{plant.id}">Momo · Monstera</option>', html=True)
        self.assertNotContains(response, 'Pas à moi')


class SimilarSpeciesTests(TestCase):

    def setUp(self):
        from Plantes.utils.species import normalize, similar_species
        self.normalize = normalize
        self.similar_species = similar_species
        self.ficus = Specie.objects.create(vernacular_name='Caoutchouc', scientific_name='Ficus elastica')
        self.monstera = Specie.objects.create(vernacular_name='Monstera', scientific_name='Monstera deliciosa')

    def test_normalisation(self):
        self.assertEqual(self.normalize('  Ficus  Élastica '), 'ficus elastica')

    def test_faute_de_frappe_detectee(self):
        matches = self.similar_species('Caoutchouk', 'Ficus elastika')

        self.assertEqual([specie for specie, score in matches], [self.ficus])
        self.assertGreaterEqual(matches[0][1], 85)

    def test_nom_eloigne_ignore(self):
        self.assertEqual(self.similar_species('Pilea', 'Pilea peperomioides'), [])

    def test_nom_latin_tape_en_nom_commun(self):
        matches = self.similar_species('monstera deliciosa', 'Monstéra délicieux')

        self.assertEqual(matches[0][0], self.monstera)
        self.assertEqual(matches[0][1], 100)


class SpeciePagesTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.ficus = Specie.objects.create(vernacular_name='Caoutchouc', scientific_name='Ficus elastica', gbif_key=1234)

    def test_catalogue_propose_d_ajouter_une_espece(self):
        response = self.client.get(reverse('list_species'))
        self.assertContains(response, 'Ajouter une espèce')
        self.assertNotContains(response, 'Ajouter une plante')

        response = self.client.get(reverse('list_species') + '?q=Pilea')
        self.assertContains(response, 'Ajouter « Pilea » au catalogue')

        response = self.client.get(reverse('add_specie') + '?name=Pilea')
        self.assertContains(response, 'name="vernacular_name" value="Pilea"')

    def test_creation_simple(self):
        response = self.client.post(reverse('add_specie'), {
            'vernacular_name': 'Pilea', 'scientific_name': 'Pilea peperomioides', 'taxon_family': 'Urticaceae',
        })

        specie = Specie.objects.get(vernacular_name='Pilea')
        self.assertRedirects(response, reverse('detail_specie', args=[specie.id]))
        self.assertIsNone(specie.gbif_key)
        self.assertEqual(specie.taxon_family, 'Urticaceae')

        response = self.client.get(reverse('detail_specie', args=[specie.id]))
        self.assertContains(response, 'espèce ajoutée à la main')
        self.assertContains(response, 'Modifier la fiche')

    def test_ressemblance_demande_confirmation(self):
        data = {'vernacular_name': 'Caoutchouk', 'scientific_name': 'Ficus elastika'}

        response = self.client.post(reverse('add_specie'), data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ressemble fort')
        self.assertContains(response, 'Caoutchouc (Ficus elastica)')
        self.assertContains(response, 'Créer quand même')
        self.assertContains(response, 'name="confirmed" value="1"')
        self.assertFalse(Specie.objects.filter(vernacular_name='Caoutchouk').exists())

        response = self.client.post(reverse('add_specie'), {**data, 'confirmed': '1'})

        specie = Specie.objects.get(vernacular_name='Caoutchouk')
        self.assertRedirects(response, reverse('detail_specie', args=[specie.id]))

    def test_creation_a_la_volee_en_json(self):
        headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'vernacular_name': 'Caoutchouk', 'scientific_name': 'Ficus elastika'}

        response = self.client.post(reverse('add_specie'), data, **headers)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['similar'][0]['id'], self.ficus.id)
        self.assertEqual(response.json()['similar'][0]['label'], 'Caoutchouc (Ficus elastica)')

        response = self.client.post(reverse('add_specie'), {**data, 'confirmed': '1'}, **headers)
        self.assertEqual(response.status_code, 200)
        specie = Specie.objects.get(vernacular_name='Caoutchouk')
        self.assertEqual(response.json(), {'id': specie.id, 'name': 'Caoutchouk (Ficus elastika)'})

        response = self.client.post(reverse('add_specie'), {'vernacular_name': 'Seul'}, **headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn('scientific_name', response.json()['errors'])

    def test_modification(self):
        response = self.client.post(reverse('edit_specie', args=[self.ficus.id]), {
            'vernacular_name': 'Caoutchouc', 'scientific_name': 'Ficus elastica', 'min_temp': 15, 'max_temp': 30,
        })

        self.assertRedirects(response, reverse('detail_specie', args=[self.ficus.id]))
        self.ficus.refresh_from_db()
        self.assertEqual((self.ficus.min_temp, self.ficus.max_temp, self.ficus.gbif_key), (15, 30, 1234))

    def test_formulaire_plante_embarque_la_boite_espece(self):
        response = self.client.get(reverse('add_plant'))

        self.assertContains(response, 'id="dialog-specie"')
        self.assertContains(response, 'data-create-dialog="dialog-specie"')
