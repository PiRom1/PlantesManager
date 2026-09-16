from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin

from .models import (
    Action,
    CareRule,
    DroughtTolerance,
    Exposure,
    Humidity,
    Notification,
    Plant,
    PlantHistory,
    PlantState,
    Pot,
    Specie,
    Spot,
    Substrate,
    User,
)


class UserAdmin(DefaultUserAdmin):
    model = User
    list_display = ['username', 'is_superuser']
    fieldsets = DefaultUserAdmin.fieldsets
    add_fieldsets = DefaultUserAdmin.add_fieldsets


admin.site.register(User, UserAdmin)


########## Generic models ##########


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'description')
    list_editable = ('code',)
    search_fields = ('name', 'code', 'description')
    ordering = ('name',)


@admin.register(Substrate)
class SubstrateAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'drying_factor', 'renew_months')
    list_editable = ('drying_factor', 'renew_months')
    list_filter = ('renew_months',)
    search_fields = ('name', 'code')
    ordering = ('name',)


@admin.register(Exposure)
class ExposureAdmin(admin.ModelAdmin):
    list_display = ('rank', 'name', 'code', 'min_lux', 'max_lux')
    list_display_links = ('name',)
    list_editable = ('min_lux', 'max_lux')
    search_fields = ('name', 'code')
    ordering = ('rank',)


@admin.register(Humidity)
class HumidityAdmin(admin.ModelAdmin):
    list_display = ('rank', 'name', 'code', 'min_HR', 'max_HR')
    list_display_links = ('name',)
    list_editable = ('min_HR', 'max_HR')
    search_fields = ('name', 'code')
    ordering = ('rank',)


@admin.register(DroughtTolerance)
class DroughtToleranceAdmin(admin.ModelAdmin):
    list_display = ('rank', 'name', 'code', 'tolerancy_days_allowed')
    list_display_links = ('name',)
    list_editable = ('tolerancy_days_allowed',)
    search_fields = ('name', 'code')
    ordering = ('rank',)


@admin.register(Specie)
class SpecieAdmin(admin.ModelAdmin):
    list_display = (
        'vernacular_name',
        'scientific_name',
        'taxon_family',
        'taxon_genus',
        'min_exposure',
        'max_exposure',
        'humidity',
        'drought_tolerance',
        'min_temp',
        'max_temp',
        'recommended_substrate',
    )
    list_filter = (
        'taxon_family',
        'taxon_genus',
        'min_exposure',
        'max_exposure',
        'humidity',
        'drought_tolerance',
        'recommended_substrate',
    )
    search_fields = (
        'vernacular_name',
        'vernacular_name_en',
        'scientific_name',
        'taxon_family',
        'taxon_genus',
        'gbif_key',
        'description',
    )
    list_select_related = (
        'min_exposure',
        'max_exposure',
        'humidity',
        'drought_tolerance',
        'recommended_substrate',
    )
    autocomplete_fields = (
        'min_exposure',
        'max_exposure',
        'humidity',
        'drought_tolerance',
        'recommended_substrate',
    )
    ordering = ('vernacular_name',)


@admin.register(Spot)
class SpotAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'exposure',
        'humidity',
        'min_temp',
        'max_temp',
        'drying_factor',
        'has_additional_light',
        'has_heater',
        'has_moister',
    )
    list_editable = ('has_additional_light', 'has_heater', 'has_moister')
    list_filter = (
        'exposure',
        'humidity',
        'has_additional_light',
        'has_heater',
        'has_moister',
    )
    search_fields = ('name', 'description')
    list_select_related = ('exposure', 'humidity')
    autocomplete_fields = ('exposure', 'humidity')
    ordering = ('name',)


@admin.register(Pot)
class PotAdmin(admin.ModelAdmin):
    list_display = ('denomination', 'material', 'volume_litre', 'drying_factor')
    list_editable = ('material', 'volume_litre', 'drying_factor')
    list_filter = ('material',)
    search_fields = ('denomination', 'material')
    ordering = ('denomination',)


@admin.register(PlantState)
class PlantStateAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'description')
    list_editable = ('code',)
    search_fields = ('name', 'code', 'description')
    ordering = ('name',)


@admin.register(CareRule)
class CareRuleAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'specie', 'plant', 'action', 'interval_days', 'month_start', 'month_end')
    list_editable = ('interval_days', 'month_start', 'month_end')
    list_filter = ('action', 'month_start', 'month_end', 'specie')
    search_fields = ('specie__vernacular_name', 'specie__scientific_name', 'action__name', 'description')
    list_select_related = ('specie', 'plant', 'action')
    autocomplete_fields = ('specie', 'plant', 'action')


########## Specific models ##########


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = (
        '__str__',
        'user',
        'specie',
        'cultivar',
        'state',
        'spot',
        'pot',
        'substrate',
        'acquisition_date',
        'creation_date',
    )
    list_filter = ('user', 'specie', 'state', 'spot', 'substrate', 'acquisition_date')
    search_fields = (
        'surname',
        'cultivar',
        'origin',
        'specie__vernacular_name',
        'specie__scientific_name',
        'user__username',
    )
    date_hierarchy = 'creation_date'
    list_select_related = ('user', 'specie', 'state', 'spot', 'pot', 'substrate')
    autocomplete_fields = ('user', 'specie', 'state', 'spot', 'pot', 'substrate', 'father')
    readonly_fields = ('creation_date',)
    ordering = ('-creation_date',)


@admin.register(PlantHistory)
class PlantHistoryAdmin(admin.ModelAdmin):
    list_display = ('plant', 'action', 'date', 'height', 'width', 'n_leaves', 'comment')
    list_filter = ('action', 'date', 'plant__specie')
    search_fields = ('plant__surname', 'comment', 'action__name')
    date_hierarchy = 'date'
    list_select_related = ('plant', 'action')
    autocomplete_fields = ('plant', 'action')
    ordering = ('-date',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('plant', 'action', 'description', 'date', 'viewed_date', 'realisation_date')
    list_filter = ('action', 'date', 'viewed_date', 'realisation_date')
    search_fields = ('plant__surname', 'action__name', 'description')
    date_hierarchy = 'date'
    list_select_related = ('plant', 'action')
    autocomplete_fields = ('plant', 'action')
    readonly_fields = ('date',)
    ordering = ('-date',)
