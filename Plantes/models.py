from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

# Create your models here.


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

    name = models.CharField(max_length=50)
    code = models.CharField(max_length=50)
    description = models.TextField()

    def __str__(self):
        return self.name



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

    vernacular_name = models.CharField(max_length=100)
    scientific_name = models.CharField(max_length=100)
    description = models.TextField(default = None, null = True, blank=True)

    ## Exigences
    min_exposure = models.ForeignKey(Exposure, related_name="species_as_min", on_delete=models.SET_NULL, null=True, blank=True)
    max_exposure = models.ForeignKey(Exposure, related_name="species_as_max", on_delete=models.SET_NULL, null=True, blank=True)
    humidity = models.ForeignKey(Humidity, on_delete=models.SET_NULL, null=True, blank=True)
    drought_tolerance = models.ForeignKey(DroughtTolerance, on_delete=models.SET_NULL, null=True, blank=True)
    min_temp = models.IntegerField(default=None, blank=True, null=True)
    max_temp = models.IntegerField(default=None, blank=True, null=True)
    recommended_substrate = models.ForeignKey(Substrate, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f'{self.vernacular_name} ({self.scientific_name})'







class Spot(models.Model):
    """
    A spot in your house where you store many plants in the same abiotic conditions
    """

    name = models.CharField(max_length=100)
    description = models.TextField(default=None, null = True, blank=True)

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


class Plant(models.Model):
    """
    A real plant, that belongs to a user
    """

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # Identity
    specie = models.ForeignKey(Specie, on_delete=models.SET_NULL, null=True, blank=True)
    image = models.ImageField(upload_to="PlantImages", default=None, null = True, blank = True)
    state = models.ForeignKey(PlantState, on_delete=models.SET_NULL, default=None, null=True, blank=True)
    acquisition_date = models.DateTimeField(default=None, null = True, blank=True)
    origin = models.CharField(max_length=50, null=True, blank=True, default=None)
    surname = models.CharField(max_length=100, null=True, blank=True, default=None) # Surnom éventuel
    acquisition_price = models.FloatField(default=None, null=True, blank=True)
    father = models.ForeignKey("self", related_name="children", default=None, null=True, blank=True, on_delete=models.SET_NULL)
    spot = models.ForeignKey(Spot, on_delete=models.SET_NULL, null=True, blank=True)
    pot = models.ForeignKey(Pot, on_delete=models.SET_NULL, null=True, blank=True)
    substrate = models.ForeignKey(Substrate, on_delete=models.SET_NULL, default=None, null=True, blank=True)
    
    creation_date = models.DateTimeField(auto_now_add=True)
    last_modification_date = models.DateTimeField(default = None, null = True, blank = True)

    def __str__(self):
        return self.surname or f'{self.specie} #{self.pk}'







class PlantHistory(models.Model):
    """
    History of a plant : actions, photos, comments, measures, ... 
    """

    plant = models.ForeignKey(Plant, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.SET_NULL, null=True, blank=True)

    # User vrac
    comment = models.TextField(default=None, blank=True, null=True)
    image = models.ImageField(upload_to="PlantImages", null=True, blank = True, default=None)
    detail = models.JSONField(default = None, null=True, blank=True)

    # Measures
    height = models.FloatField(default=None, null=True, blank=True)
    width = models.FloatField(default=None, null=True, blank=True)
    n_leaves = models.IntegerField(default=None, null=True, blank=True)

    date = models.DateTimeField()

    def __str__(self):
        return f'{self.plant} - {self.action} ({self.date:%d/%m/%Y})'



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

