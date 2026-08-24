from django.contrib import admin

from core.models import (
    AliasCentroCosto,
    CentroCosto,
    ParametroNegocio,
    ParametroValor,
)


@admin.register(CentroCosto)
class CentroCostoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo", "padre", "activo")
    list_filter = ("tipo", "activo")
    search_fields = ("codigo", "nombre")


@admin.register(AliasCentroCosto)
class AliasCentroCostoAdmin(admin.ModelAdmin):
    list_display = ("alias", "centro_costo")
    search_fields = ("alias", "centro_costo__codigo")


class ParametroValorInline(admin.TabularInline):
    model = ParametroValor
    extra = 0


@admin.register(ParametroNegocio)
class ParametroNegocioAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")
    inlines = [ParametroValorInline]
