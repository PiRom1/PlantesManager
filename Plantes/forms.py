# Formulaires de l'application Plantes.

from django import forms

from Plantes.models import Plant, PlantHistory, Pot, PropagationMedium, PropagationMethod, Room, Specie, Spot


class PlantForm(forms.ModelForm):
    """
    Création et modification d'une plante.

    Le propriétaire n'est pas exposé : il est forcé à request.user dans la vue.
    L'espèce passe par un champ caché alimenté par l'autocomplétion : avec
    plusieurs milliers d'espèces, un menu déroulant est inutilisable.
    """

    class Meta:
        model = Plant
        fields = [
            'specie',
            'cultivar',
            'surname',
            'state',
            'spot',
            'pot',
            'substrate',
            'has_additional_light',
            'has_heater',
            'has_moister',
            'father',
            'acquisition_date',
            'acquisition_price',
            'origin',
            'image',
        ]
        widgets = {
            'specie': forms.HiddenInput(),
            'cultivar': forms.TextInput(attrs={'placeholder': 'Variegata, ...'}),
            # Format ISO imposé : avec la locale fr, le navigateur refuserait « 14/10/2026 »
            # et afficherait un champ vide, même pour une date existante
            'acquisition_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }
        labels = {
            'specie': 'Espèce',
            'cultivar': 'Cultivar',
            'surname': 'Surnom',
            'state': 'État',
            'spot': 'Emplacement',
            'pot': 'Pot',
            'substrate': 'Substrat',
            'has_additional_light': "Éclairage d'appoint",
            'has_heater': 'Chauffage',
            'has_moister': 'Humidificateur',
            'father': 'Plante mère',
            'acquisition_date': "Date d'acquisition",
            'acquisition_price': "Prix d'acquisition (€)",
            'origin': 'Origine',
            'image': 'Photo',
        }
        error_messages = {
            'specie': {
                'required': 'Choisis une espèce dans la liste des suggestions.',
                'invalid_choice': 'Choisis une espèce dans la liste des suggestions.',
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Le modèle tolère une plante sans espèce (SET_NULL si l'espèce est
        # supprimée du catalogue), mais la saisie, elle, doit en désigner une
        self.fields['specie'].required = True

        # Le surnom seul ne dit pas de quelle plante il s'agit
        self.fields['father'].label_from_instance = lambda plant: plant.choice_label

        # L'état ne se choisit qu'à la création. Ensuite, il découle du journal :
        # un changement ou une correction passe par une entrée du journal
        if self.instance.pk:
            del self.fields['state']


class PlantImageForm(forms.ModelForm):
    """Changement de la seule photo d'une plante, depuis sa fiche."""

    class Meta:
        model = Plant
        fields = ['image']
        labels = {'image': 'Photo'}


class RoomForm(forms.ModelForm):
    """Pièce de la maison : un nom, et c'est tout ; les conditions sont sur l'emplacement."""

    class Meta:
        model = Room
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Salon, chambre, véranda, ...'}),
            'description': forms.Textarea(attrs={'rows': 2}),
        }
        labels = {
            'name': 'Nom',
            'description': 'Description',
        }

    def __init__(self, *args, **kwargs):
        # Ce formulaire cohabite avec celui de l'emplacement (mêmes noms de
        # champs) dans la même page : les identifiants HTML doivent différer
        kwargs.setdefault('auto_id', 'id_room_%s')
        super().__init__(*args, **kwargs)


class SpotForm(forms.ModelForm):
    """
    Emplacement : un endroit de la maison aux conditions homogènes.

    `user` limite le menu des pièces aux siennes.
    """

    class Meta:
        model = Spot
        fields = [
            'name',
            'room',
            'description',
            'exposure',
            'humidity',
            'min_temp',
            'max_temp',
            'drying_factor',
            'has_additional_light',
            'has_heater',
            'has_moister',
        ]
        labels = {
            'name': 'Nom',
            'room': 'Pièce',
            'description': 'Description',
            'exposure': 'Exposition',
            'humidity': 'Humidité',
            'min_temp': 'Température minimale (°C)',
            'max_temp': 'Température maximale (°C)',
            'drying_factor': 'Facteur de séchage',
            'has_additional_light': "Éclairage d'appoint",
            'has_heater': 'Chauffage',
            'has_moister': 'Humidificateur',
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['room'].queryset = Room.objects.filter(user=user).order_by('name')
        self.fields['room'].empty_label = 'Aucune'


class PotForm(forms.ModelForm):
    """Pot dans lequel une plante est installée."""

    class Meta:
        model = Pot
        fields = [
            'denomination',
            'material',
            'volume_litre',
            'drying_factor',
        ]
        labels = {
            'denomination': 'Dénomination',
            'material': 'Matériau',
            'volume_litre': 'Volume (litres)',
            'drying_factor': 'Facteur de séchage',
        }


class PlantHistoryForm(forms.ModelForm):
    """
    Entrée du journal d'une plante : une action réalisée, avec photo,
    commentaire et mesures éventuelles.

    Le champ `detail` (JSON) est volontairement absent : il n'a rien à faire
    dans un formulaire utilisateur.
    """

    class Meta:
        model = PlantHistory
        fields = [
            'action',
            'state',
            'date',
            'comment',
            'image',
            'height',
            'width',
            'n_leaves',
        ]
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'comment': forms.Textarea(attrs={'rows': 3}),
            'image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }
        labels = {
            'action': 'Action',
            'state': 'Nouvel état',
            'date': 'Date',
            'comment': 'Commentaire',
            'image': 'Photo',
            'height': 'Hauteur (cm)',
            'width': 'Largeur (cm)',
            'n_leaves': 'Nombre de feuilles',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Le navigateur n'accepte que ce format pour datetime-local
        self.fields['date'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S']

        # Une entrée n'est pas forcément une action : un simple constat suffit
        self.fields['action'].empty_label = 'Aucune, simple constat'
        self.fields['state'].empty_label = 'Inchangé'

    def clean(self):
        cleaned_data = super().clean()

        # Au moins une information, sinon l'entrée ne dit rien
        filled = [cleaned_data.get(name) for name in
                  ['action', 'state', 'comment', 'image', 'height', 'width', 'n_leaves']]

        if not any(value not in (None, '') for value in filled):
            raise forms.ValidationError(
                'Entrée vide : indique au moins une action, un état, un commentaire, une photo ou une mesure.')

        return cleaned_data


class PropagationForm(forms.Form):
    """
    Détails du bouturage, saisis en déclarant une bouture depuis la plante mère.
    Tout est optionnel : ils alimentent l'entrée « Bouturage » du journal de la
    mère, dont le schéma est Action.DETAIL_FIELDS['PROPAGATE'].
    """

    method = forms.ChoiceField(label='Méthode', required=False,
                               choices=[('', '—')] + PropagationMethod.choices)
    medium = forms.ChoiceField(label='Milieu', required=False,
                               choices=[('', '—')] + PropagationMedium.choices)
    hormone = forms.BooleanField(label='Hormone de bouturage', required=False)


class SpecieForm(forms.ModelForm):
    """
    Espèce créée ou modifiée à la main. Les deux noms suffisent, le reste est
    optionnel. La clé GBIF n'est pas exposée : une espèce saisie ici n'en a pas,
    et celle d'une espèce importée ne se touche pas.
    """

    class Meta:
        model = Specie
        fields = [
            'vernacular_name',
            'scientific_name',
            'vernacular_name_en',
            'description',
            'image',
            'taxon_family',
            'taxon_genus',
            'min_exposure',
            'max_exposure',
            'humidity',
            'drought_tolerance',
            'min_temp',
            'max_temp',
            'recommended_substrate',
            'abiotic_conditions',
        ]
        widgets = {
            'vernacular_name': forms.TextInput(attrs={'placeholder': 'Monstera, Pilea, ...'}),
            'scientific_name': forms.TextInput(attrs={'placeholder': 'Genre espèce, en latin'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'abiotic_conditions': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': "Lumière vive sans soleil direct, substrat qui sèche entre deux arrosages, craint les courants d'air...",
            }),
        }
        labels = {
            'vernacular_name': 'Nom commun',
            'scientific_name': 'Nom scientifique',
            'vernacular_name_en': 'Nom commun en anglais',
            'description': 'Description',
            'image': 'Planche',
            'taxon_family': 'Famille',
            'taxon_genus': 'Genre',
            'min_exposure': 'Exposition minimale',
            'max_exposure': 'Exposition maximale',
            'humidity': 'Humidité',
            'drought_tolerance': 'Tolérance à la sécheresse',
            'min_temp': 'Température minimale (°C)',
            'max_temp': 'Température maximale (°C)',
            'recommended_substrate': 'Substrat conseillé',
            'abiotic_conditions': 'Conditions abiotiques favorables',
        }
        help_texts = {
            'abiotic_conditions': "Tes notes de lecture sur ce qui convient à l'espèce. Affichées sur la fiche de chacune de tes plantes de cette espèce.",
        }
