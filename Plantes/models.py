from dataclasses import dataclass
from functools import cached_property

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


########## Chemins d'upload ##########


def specie_image_path(instance, filename):
    """media/SpecieImages/<gbif_key>/<filename>"""
    return f'SpecieImages/{instance.gbif_key or instance.pk or "unsorted"}/{filename}'


def plant_image_path(instance, filename):
    """media/PlantImages/<plant_id>/<filename>"""
    return f'PlantImages/{instance.pk or "unsorted"}/{filename}'


def plant_history_image_path(instance, filename):
    """media/PlantImages/<plant_id>/history/<filename>"""
    return f'PlantImages/{instance.plant_id or "unsorted"}/history/{filename}'


class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        """
        Creates and saves a user with the given email and password.
        """
        user = self.model(
            email=self.normalize_email(email),
            **extra_fields
        )

        user.set_password(password)
        user.is_active = True
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
            **extra_fields
        )

        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save(using=self._db)
        return user


class User(AbstractUser):
    objects = UserManager()
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Utilisateur'

    def __str__(self):
        return f'{self.username}'


########## Détail des actions ##########


class DetailFieldType(models.TextChoices):
    """Types de champ acceptés dans Action.DETAIL_FIELDS."""

    SELECT = 'select', 'Liste de choix'
    INTEGER = 'integer', 'Nombre entier'
    DECIMAL = 'decimal', 'Nombre décimal'
    TEXT = 'text', 'Texte libre'
    BOOLEAN = 'boolean', 'Oui / non'
    TAGS = 'tags', 'Choix multiples et saisie libre'


class WaterType(models.TextChoices):
    TAP = 'TAP', 'Robinet'
    RAIN = 'RAIN', 'Pluie'
    DEMINERALIZED = 'DEMINERALIZED', 'Déminéralisée'
    FILTERED = 'FILTERED', 'Filtrée'


class WateringMethod(models.TextChoices):
    SURFACE = 'SURFACE', 'En surface'
    SOAKING = 'SOAKING', 'Par bassinage'
    DRIP = 'DRIP', 'Goutte-à-goutte'


class FertilizerForm(models.TextChoices):
    LIQUID = 'LIQUID', 'Liquide'
    STICK = 'STICK', 'Bâtonnet'
    GRANULES = 'GRANULES', 'Granulés'
    ORGANIC = 'ORGANIC', 'Organique'


class PruneType(models.TextChoices):
    MAINTENANCE = 'MAINTENANCE', 'Entretien'
    SHAPING = 'SHAPING', 'Mise en forme'
    TOPPING = 'TOPPING', 'Étêtage'
    ROOTS = 'ROOTS', 'Racines'


class RepotReason(models.TextChoices):
    ROOT_BOUND = 'ROOT_BOUND', "Racines à l'étroit"
    GROWTH = 'GROWTH', 'Croissance'
    PURCHASE = 'PURCHASE', 'Achat'


class RootState(models.TextChoices):
    HEALTHY = 'HEALTHY', 'Saines'
    SOME_DEAD = 'SOME_DEAD', 'Quelques racines mortes'
    ROT = 'ROT', 'Pourriture'


class SubstrateChangeReason(models.TextChoices):
    SPENT = 'SPENT', 'Épuisé'
    UNSUITABLE = 'UNSUITABLE', 'Inadapté'
    CONTAMINATED = 'CONTAMINATED', 'Contaminé'


class MoveReason(models.TextChoices):
    NOT_ENOUGH_LIGHT = 'NOT_ENOUGH_LIGHT', 'Lumière insuffisante'
    TOO_MUCH_SUN = 'TOO_MUCH_SUN', 'Trop de soleil'
    DRAFT = 'DRAFT', "Courant d'air"
    TEMPERATURE = 'TEMPERATURE', 'Température'
    HUMIDITY = 'HUMIDITY', 'Humidité'
    REARRANGEMENT = 'REARRANGEMENT', 'Réaménagement'


class CleaningMethod(models.TextChoices):
    DAMP_CLOTH = 'DAMP_CLOTH', 'Chiffon humide'
    SHOWER = 'SHOWER', 'Douche'
    SPRAY = 'SPRAY', 'Pulvérisation'


class PestCheckResult(models.TextChoices):
    # Seule une inspection « Absence » clôt un épisode parasitaire :
    # un traitement ne dit rien de son efficacité
    CLEAR = 'CLEAR', 'Absence'
    SUSPICION = 'SUSPICION', 'Suspicion'
    CONFIRMED = 'CONFIRMED', 'Présence'


class Pest(models.TextChoices):
    # Choix proposés : le champ accepte aussi n'importe quel nom tapé à la main
    MEALYBUG = 'MEALYBUG', 'Cochenille farineuse'
    SCALE = 'SCALE', 'Cochenille à bouclier'
    SPIDER_MITE = 'SPIDER_MITE', 'Araignées rouges'
    THRIPS = 'THRIPS', 'Thrips'
    APHID = 'APHID', 'Pucerons'
    FUNGUS_GNAT = 'FUNGUS_GNAT', 'Mouches du terreau'


class PestSeverity(models.TextChoices):
    LIGHT = 'LIGHT', 'Légère'
    MODERATE = 'MODERATE', 'Modérée'
    SEVERE = 'SEVERE', 'Sévère'


class PestTreatment(models.TextChoices):
    # Choix proposés : le champ accepte aussi un produit tapé à la main
    MANUAL = 'MANUAL', 'Retrait manuel'
    SHOWER = 'SHOWER', 'Douche ou rinçage'
    BLACK_SOAP = 'BLACK_SOAP', 'Savon noir'
    NEEM = 'NEEM', 'Huile de neem'
    ALCOHOL = 'ALCOHOL', 'Alcool à 70°'
    INSECTICIDE = 'INSECTICIDE', 'Insecticide chimique'
    BENEFICIALS = 'BENEFICIALS', 'Auxiliaires (coccinelles, nématodes...)'
    STICKY_TRAPS = 'STICKY_TRAPS', 'Pièges collants jaunes'
    QUARANTINE = 'QUARANTINE', 'Mise en quarantaine'


class PropagationMethod(models.TextChoices):
    STEM_CUTTING = 'STEM_CUTTING', 'Bouture de tige'
    LEAF_CUTTING = 'LEAF_CUTTING', 'Bouture de feuille'
    LAYERING = 'LAYERING', 'Marcottage'
    DIVISION = 'DIVISION', 'Division'
    SEED = 'SEED', 'Semis'


class PropagationMedium(models.TextChoices):
    WATER = 'WATER', 'Eau'
    SOIL = 'SOIL', 'Terreau'
    SPHAGNUM = 'SPHAGNUM', 'Sphaigne'
    PERLITE = 'PERLITE', 'Perlite'


@dataclass(frozen=True)
class DetailField:
    """
    Un champ de détail saisi lors d'une action.

    `choices` n'a de sens que pour un champ SELECT (obligatoires) ou TAGS
    (suggestions, la saisie libre reste possible) ; la cohérence est vérifiée
    à l'import, donc une faute de frappe casse au démarrage plutôt que de
    passer inaperçue au rendu.
    """

    name: str
    label: str
    type: str
    choices: tuple = ()
    # Champ conditionnel : (nom d'un champ select de la même action, valeurs qui
    # l'affichent). Masqué dans le formulaire et ignoré au POST sinon.
    shown_when: tuple = ()

    def __post_init__(self):
        if self.type not in DetailFieldType.values:
            raise ValueError(f"{self.name} : type '{self.type}' inconnu")

        if self.type == DetailFieldType.SELECT and not self.choices:
            raise ValueError(f'{self.name} : un champ select doit avoir des choix')

        if self.type not in (DetailFieldType.SELECT, DetailFieldType.TAGS) and self.choices:
            raise ValueError(f"{self.name} : seuls les champs select et tags acceptent des choix")

        if self.shown_when and (len(self.shown_when) != 2 or not self.shown_when[1]):
            raise ValueError(f'{self.name} : shown_when attend (champ, (valeurs...))')

    def is_shown(self, detail):
        """Le champ a-t-il lieu d'être, vu les autres valeurs saisies ?"""

        if not self.shown_when:
            return True

        field, values = self.shown_when

        return detail.get(field) in values

    def display(self, value):
        """Valeur stockée dans le JSON rendue lisible : libellés à la place des codes."""

        if self.type == DetailFieldType.SELECT:
            return dict(self.choices).get(value, value)

        if self.type == DetailFieldType.BOOLEAN:
            return 'oui' if value else 'non'

        if self.type == DetailFieldType.TAGS:
            labels = dict(self.choices)
            values = value if isinstance(value, list) else [value]
            return ', '.join(str(labels.get(item, item)) for item in values)

        return value


########## Generic models ##########


class Action(models.Model):
    """
    Feasible actions on a plant :
        - Water
        - Prune
        - Move from a room to another
        - Change pot
        - Change soil
        - ...
    """

    # Champs de détail saisis lors de la réalisation de l'action, par code.
    # Seule source de vérité : le formulaire, la validation au POST et
    # l'affichage de l'historique sont tous construits à partir d'ici.
    # Types acceptés : 'select', 'integer', 'decimal', 'text', 'boolean', 'tags'.
    DETAIL_FIELDS = {

        'WATER': [
            DetailField('water_type', "Type d'eau", DetailFieldType.SELECT, WaterType.choices),
            DetailField('volume_ml', 'Volume (mL)', DetailFieldType.INTEGER),
            DetailField('method', 'Méthode', DetailFieldType.SELECT, WateringMethod.choices),
            DetailField('runoff', 'Écoulement par le fond', DetailFieldType.BOOLEAN),
        ],

        'MIST': [
            DetailField('water_type', "Type d'eau", DetailFieldType.SELECT, WaterType.choices),
            DetailField('n_sprays', 'Nombre de sprays', DetailFieldType.INTEGER),
        ],

        'FERTILIZE': [
            DetailField('fertilizer_form', 'Forme', DetailFieldType.SELECT, FertilizerForm.choices),
            DetailField('npk', 'NPK', DetailFieldType.TEXT),
            DetailField('dose', 'Dose (mL ou g par litre)', DetailFieldType.DECIMAL),
        ],

        'PRUNE': [
            DetailField('prune_type', 'Type de taille', DetailFieldType.SELECT, PruneType.choices),
            DetailField('removed_leaves', 'Feuilles retirées', DetailFieldType.INTEGER),
        ],

        'REPOT': [
            DetailField('reason', 'Motif', DetailFieldType.SELECT, RepotReason.choices),
            DetailField('root_state', 'État des racines', DetailFieldType.SELECT, RootState.choices),
            DetailField('roots_pruned', 'Racines taillées', DetailFieldType.BOOLEAN),
        ],

        'CHANGE_SUBSTRATE': [
            DetailField('reason', 'Motif', DetailFieldType.SELECT, SubstrateChangeReason.choices),
            DetailField('amendment', 'Amendement ajouté', DetailFieldType.TEXT),
        ],

        'MOVE': [
            DetailField('reason', 'Motif', DetailFieldType.SELECT, MoveReason.choices),
        ],

        'CLEAN_LEAVES': [
            DetailField('method', 'Méthode', DetailFieldType.SELECT, CleaningMethod.choices),
            DetailField('product', 'Produit', DetailFieldType.TEXT),
        ],

        # L'inspection constate, le traitement agit : seule une inspection
        # « Absence » met fin à un épisode parasitaire (voir Plant.pest_episode)
        'CHECK_PESTS': [
            DetailField('result', 'Résultat', DetailFieldType.SELECT, PestCheckResult.choices),
            DetailField('pests', 'Parasites', DetailFieldType.TAGS, Pest.choices,
                        shown_when=('result', (PestCheckResult.SUSPICION, PestCheckResult.CONFIRMED))),
            DetailField('severity', 'Gravité', DetailFieldType.SELECT, PestSeverity.choices,
                        shown_when=('result', (PestCheckResult.SUSPICION, PestCheckResult.CONFIRMED))),
        ],

        'TREAT_PESTS': [
            DetailField('pests', 'Parasites ciblés', DetailFieldType.TAGS, Pest.choices),
            DetailField('treatment', 'Traitement', DetailFieldType.TAGS, PestTreatment.choices),
            DetailField('dose', 'Dose ou dilution', DetailFieldType.TEXT),
        ],

        'PROPAGATE': [
            DetailField('method', 'Méthode', DetailFieldType.SELECT, PropagationMethod.choices),
            DetailField('medium', 'Milieu', DetailFieldType.SELECT, PropagationMedium.choices),
            DetailField('n_cuttings', 'Nombre de boutures', DetailFieldType.INTEGER),
            DetailField('hormone', 'Hormone de bouturage', DetailFieldType.BOOLEAN),
        ],
    }

    name = models.CharField(max_length=50)
    code = models.CharField(max_length=50)
    description = models.TextField()

    def __str__(self):
        return self.name

    @property
    def detail_fields(self):
        """Champs de détail de cette action (liste vide si elle n'en a pas)."""

        return self.DETAIL_FIELDS.get(self.code, [])

    @classmethod
    def detail_field(cls, code, name):
        """Le champ de détail `name` de l'action `code`, pour lire un JSON hors du journal."""

        for field in cls.DETAIL_FIELDS.get(code, []):
            if field.name == name:
                return field

        raise KeyError(f'{code} : pas de champ de détail {name}')



class Substrate(models.Model):
    """
    A soil type
    """

    name = models.CharField(max_length=50)
    code = models.CharField(max_length=50)
    description = models.TextField(default=None, null=True, blank=True)
    drying_factor = models.FloatField()
    renew_months = models.IntegerField(default=None, null=True, blank=True)

    def __str__(self):
        return self.name



class Exposure(models.Model):
    """
    Exposure scale
    """

    name = models.CharField(max_length=50)
    code = models.CharField(max_length=50)
    min_lux = models.IntegerField()
    max_lux = models.IntegerField()
    rank = models.IntegerField()

    def __str__(self):
        return self.name



class Humidity(models.Model):
    """
    Humidity scale
    """

    name = models.CharField(max_length=50)
    code = models.CharField(max_length=50)
    min_HR = models.IntegerField()
    max_HR = models.IntegerField()
    rank = models.IntegerField()

    def __str__(self):
        return self.name



class DroughtTolerance(models.Model):
    """
    Tolérance à la sécheresse (en nb de jours)
    """

    name = models.CharField(max_length=50)
    code = models.CharField(max_length=50)
    tolerancy_days_allowed = models.IntegerField()
    rank = models.IntegerField()

    def __str__(self):
        return self.name



class Specie(models.Model):
    """
    A plant specimen
    """

    gbif_key = models.BigIntegerField(unique=True, default=None, null=True, blank=True)

    vernacular_name = models.CharField(max_length=500)
    vernacular_name_en = models.CharField(max_length=500, default=None, null=True, blank=True)
    scientific_name = models.CharField(max_length=100)
    description = models.TextField(default = None, null = True, blank=True)
    image = models.ImageField(upload_to=specie_image_path, default=None, null=True, blank=True)

    ## Taxonomie (source GBIF)
    taxon_class = models.CharField(max_length=50, default=None, null=True, blank=True)
    taxon_order = models.CharField(max_length=50, default=None, null=True, blank=True)
    taxon_family = models.CharField(max_length=50, default=None, null=True, blank=True)
    taxon_genus = models.CharField(max_length=50, default=None, null=True, blank=True)

    ## Exigences
    min_exposure = models.ForeignKey(Exposure, related_name="species_as_min", on_delete=models.SET_NULL, null=True, blank=True)
    max_exposure = models.ForeignKey(Exposure, related_name="species_as_max", on_delete=models.SET_NULL, null=True, blank=True)
    humidity = models.ForeignKey(Humidity, on_delete=models.SET_NULL, null=True, blank=True)
    drought_tolerance = models.ForeignKey(DroughtTolerance, on_delete=models.SET_NULL, null=True, blank=True)
    min_temp = models.IntegerField(default=None, blank=True, null=True)
    max_temp = models.IntegerField(default=None, blank=True, null=True)
    recommended_substrate = models.ForeignKey(Substrate, on_delete=models.SET_NULL, null=True, blank=True)

    # Notes de lecture en texte libre, en complément des champs structurés
    # ci-dessus : ce qu'on retient des conditions qui conviennent à l'espèce
    abiotic_conditions = models.TextField(default=None, null=True, blank=True)

    def __str__(self):
        return f'{self.vernacular_name} ({self.scientific_name})'







class Room(models.Model):
    """
    A room of your house. The abiotic conditions live on the spots inside it :
    the room only tells where a spot is.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None, null=True, blank=True)

    name = models.CharField(max_length=100)
    description = models.TextField(default=None, null=True, blank=True)

    def __str__(self):
        return self.name



class Spot(models.Model):
    """
    A spot in your house where you store many plants in the same abiotic conditions
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None, null=True, blank=True)

    name = models.CharField(max_length=100)
    description = models.TextField(default=None, null = True, blank=True)
    # Nullable : les emplacements existants n'ont pas de pièce, à rattacher à la main
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)

    exposure = models.ForeignKey(Exposure, on_delete=models.SET_NULL, null=True, blank=True)
    humidity = models.ForeignKey(Humidity, on_delete=models.SET_NULL, null=True, blank=True)
    min_temp = models.IntegerField(default=None, blank=True, null=True)
    max_temp = models.IntegerField(default=None, blank=True, null=True)

    drying_factor = models.FloatField(default=1.0)
    has_additional_light = models.BooleanField(default = False)
    has_heater = models.BooleanField(default = False)
    has_moister = models.BooleanField(default = False)

    def __str__(self):
        return self.name





class Pot(models.Model):
    """
    A generic pot where you install a plant
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None, null=True, blank=True)

    denomination = models.CharField(max_length=100)
    material = models.CharField(max_length=50, blank=True, null=True, default=None)
    volume_litre = models.IntegerField(blank=True, null=True, default=None)
    drying_factor = models.FloatField(default=1.0)

    def __str__(self):
        return self.denomination







class PlantState(models.Model):
    """
    Possible living states of a plant :
        - Dormance
        - Jeune pousse
        - Bouture
        - Croissance
        - ...
    """

    name = models.CharField(max_length=50)
    code = models.CharField(max_length=50)
    description = models.TextField()

    def __str__(self):
        return self.name




class CareRule(models.Model):
    """
    Cadence d'une action, pour une espèce (défaut) ou pour une plante (surcharge).
    Exactement un des deux parmi specie / plant doit être renseigné.
    Pas de règle sur un mois donné = rien à faire ce mois-là.
    """

    specie = models.ForeignKey(Specie, related_name="care_rules", on_delete=models.CASCADE, default=None, null=True, blank=True)
    plant = models.ForeignKey("Plant", related_name="care_rules", on_delete=models.CASCADE, default=None, null=True, blank=True)
    action = models.ForeignKey(Action, related_name="care_rules", on_delete=models.CASCADE)

    interval_days = models.IntegerField()
    month_start = models.IntegerField(default=1)   # 1 = janvier
    month_end = models.IntegerField(default=12)    # 12 = décembre

    description = models.TextField(default=None, null=True, blank=True)

    def __str__(self):
        return f'{self.action} - {self.specie or self.plant}'


########## Specific models ##########


@dataclass(frozen=True)
class PestEpisode:
    """
    Épisode parasitaire en cours d'une plante, déduit de son journal.

    `inspections` : les inspections positives (suspicion ou présence) depuis la
    dernière « Absence », de la plus ancienne à la plus récente. `treatments` :
    les traitements notés depuis la première, de la plus récente à la plus
    ancienne.
    """

    inspections: list
    treatments: list

    @property
    def opening(self):
        return self.inspections[0]

    @property
    def latest(self):
        return self.inspections[-1]

    @property
    def since(self):
        return self.opening.date

    @property
    def result(self):
        return (self.latest.detail or {}).get('result')

    @property
    def confirmed(self):
        return self.result == PestCheckResult.CONFIRMED

    @property
    def result_label(self):
        return Action.detail_field('CHECK_PESTS', 'result').display(self.result)

    @property
    def pest_codes(self):
        """Parasites cités au fil de l'épisode, les plus récents d'abord, sans doublon."""

        codes = []

        for inspection in reversed(self.inspections):
            for code in (inspection.detail or {}).get('pests') or []:
                if code not in codes:
                    codes.append(code)

        return codes

    @property
    def pests(self):
        return Action.detail_field('CHECK_PESTS', 'pests').display(self.pest_codes)

    @property
    def severity(self):
        severity = (self.latest.detail or {}).get('severity')

        return Action.detail_field('CHECK_PESTS', 'severity').display(severity) if severity else None

    @property
    def treatment_lines(self):
        """Traitements de l'épisode, lisibles : (entrée, traitement, dose)."""

        field = Action.detail_field('TREAT_PESTS', 'treatment')
        lines = []

        for entry in self.treatments:
            detail = entry.detail or {}
            treatment = field.display(detail.get('treatment') or []) or 'Traitement non précisé'
            lines.append((entry, treatment, detail.get('dose')))

        return lines


class Plant(models.Model):
    """
    A real plant, that belongs to a user
    """

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # Identity
    specie = models.ForeignKey(Specie, on_delete=models.SET_NULL, null=True, blank=True)
    cultivar = models.CharField(max_length=100, default=None, null=True, blank=True)
    image = models.ImageField(upload_to=plant_image_path, default=None, null = True, blank = True)
    state = models.ForeignKey(PlantState, on_delete=models.SET_NULL, default=None, null=True, blank=True)
    acquisition_date = models.DateField(default=None, null = True, blank=True)
    origin = models.CharField(max_length=50, null=True, blank=True, default=None)
    surname = models.CharField(max_length=100, null=True, blank=True, default=None) # Surnom éventuel
    acquisition_price = models.FloatField(default=None, null=True, blank=True)
    father = models.ForeignKey("self", related_name="children", default=None, null=True, blank=True, on_delete=models.SET_NULL)
    spot = models.ForeignKey(Spot, on_delete=models.SET_NULL, null=True, blank=True)
    pot = models.ForeignKey(Pot, on_delete=models.SET_NULL, null=True, blank=True)
    substrate = models.ForeignKey(Substrate, on_delete=models.SET_NULL, default=None, null=True, blank=True)

    # Équipement propre à la plante, qui se cumule avec celui de l'emplacement
    has_additional_light = models.BooleanField(default=False)
    has_heater = models.BooleanField(default=False)
    has_moister = models.BooleanField(default=False)

    creation_date = models.DateTimeField(auto_now_add=True)
    last_modification_date = models.DateTimeField(auto_now=True, null = True, blank = True)

    EQUIPMENT_LABELS = [
        ('has_additional_light', "Éclairage d'appoint"),
        ('has_heater', 'Chauffage'),
        ('has_moister', 'Humidificateur'),
    ]

    def __str__(self):
        if self.surname:
            return self.surname
        specie = f"{self.specie} '{self.cultivar}'" if self.cultivar else f'{self.specie}'
        return f'{specie} #{self.pk}'

    @property
    def choice_label(self):
        """
        Libellé dans un menu déroulant : le surnom seul ne dit pas de quelle
        plante il s'agit, on lui adjoint le nom commun. Sans surnom, le libellé
        courant contient déjà l'espèce.
        """

        if self.surname and self.specie:
            return f'{self.surname} · {self.specie.vernacular_name}'

        return str(self)

    def refresh_state(self):
        """
        Le journal fait foi : l'état de la plante est celui de la dernière entrée
        qui en porte un. Aucune entrée avec un état = pas d'état.
        """

        last = (self.planthistory_set
                .filter(state__isnull=False)
                .order_by('-date', '-id')
                .first())

        self.state = last.state if last else None
        self.save(update_fields=['state'])

    @property
    def equipment(self):
        """
        Équipement effectif : celui de l'emplacement et celui de la plante se
        cumulent. Liste de (libellé, provenance).
        """

        items = []

        for field, label in self.EQUIPMENT_LABELS:
            own = getattr(self, field)
            from_spot = bool(self.spot and getattr(self.spot, field))

            if own and from_spot:
                items.append((label, 'plante et emplacement'))
            elif own:
                items.append((label, 'plante'))
            elif from_spot:
                items.append((label, 'emplacement'))

        return items

    @cached_property
    def pest_episode(self):
        """
        Épisode parasitaire en cours, déduit du journal, ou None.

        Seule une inspection fait foi : l'épisode s'ouvre à la première
        inspection positive (suspicion ou présence) qui suit la dernière
        inspection « Absence », et reste ouvert tant qu'aucune inspection ne
        constate l'absence. Les traitements notés depuis l'ouverture sont
        joints mais ne ferment jamais l'épisode : un traitement ne dit rien
        de son efficacité.
        """

        entries = list(self.planthistory_set
                       .filter(action__code__in=['CHECK_PESTS', 'TREAT_PESTS'])
                       .select_related('action')
                       .order_by('date', 'id'))

        inspections = []

        for entry in entries:
            if entry.action.code != 'CHECK_PESTS':
                continue

            result = (entry.detail or {}).get('result')

            if result in (PestCheckResult.SUSPICION, PestCheckResult.CONFIRMED):
                inspections.append(entry)
            elif result == PestCheckResult.CLEAR:
                inspections = []
            # Inspection sans résultat : elle ne dit rien, on l'ignore

        if not inspections:
            return None

        opening = inspections[0]
        treatments = [entry for entry in entries
                      if entry.action.code == 'TREAT_PESTS'
                      and (entry.date, entry.id) >= (opening.date, opening.id)]

        return PestEpisode(inspections=inspections, treatments=treatments[::-1])







class PlantHistory(models.Model):
    """
    History of a plant : actions, photos, comments, measures, ... 
    """

    plant = models.ForeignKey(Plant, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.SET_NULL, null=True, blank=True)
    state = models.ForeignKey(PlantState, on_delete=models.SET_NULL, default=None, null=True, blank=True) # Nouvel état constaté

    # User vrac
    comment = models.TextField(default=None, blank=True, null=True)
    image = models.ImageField(upload_to=plant_history_image_path, null=True, blank = True, default=None)
    detail = models.JSONField(default = None, null=True, blank=True)

    # Measures
    height = models.FloatField(default=None, null=True, blank=True)
    width = models.FloatField(default=None, null=True, blank=True)
    n_leaves = models.IntegerField(default=None, null=True, blank=True)

    date = models.DateTimeField()

    def __str__(self):
        return f'{self.plant} - {self.action} ({self.date:%d/%m/%Y})'

    @property
    def detail_summary(self):
        """
        Contenu de `detail` traduit en paires (libellé, valeur lisible),
        d'après le schéma porté par l'action.
        """

        if not self.detail or not self.action:
            return []

        summary = []

        for field in self.action.detail_fields:
            if field.name not in self.detail:
                continue

            summary.append((field.label, field.display(self.detail[field.name])))

        return summary



class Notification(models.Model):
    """
    Actions to do, indicated to the user
    """

    plant = models.ForeignKey(Plant, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    viewed_date = models.DateTimeField(default = None, null = True, blank = True) # A été vue
    realisation_date = models.DateTimeField(default = None, null = True, blank = True) # A été faite

    def __str__(self):
        return f'{self.plant} - {self.action}'

