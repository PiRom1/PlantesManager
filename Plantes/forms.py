# Formulaires de l'application Plantes.

from django import forms

from Plantes.models import Plant, PlantHistory, Pot, Spot


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
            'father',
            'acquisition_date',
            'acquisition_price',
            'origin',
            'image',
        ]
        widgets = {
            'specie': forms.HiddenInput(),
            'acquisition_date': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'specie': 'Espèce',
            'cultivar': 'Cultivar',
            'surname': 'Surnom',
            'state': 'État',
            'spot': 'Emplacement',
            'pot': 'Pot',
            'substrate': 'Substrat',
            'father': 'Plante mère',
            'acquisition_date': "Date d'acquisition",
            'acquisition_price': "Prix d'acquisition (€)",
            'origin': 'Origine',
            'image': 'Photo',
        }


class SpotForm(forms.ModelForm):
    """Emplacement : un endroit de la maison aux conditions homogènes."""

    class Meta:
        model = Spot
        fields = [
            'name',
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
        }
        labels = {
            'action': 'Action',
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
