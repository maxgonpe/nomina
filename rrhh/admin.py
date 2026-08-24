from django.contrib import admin

from rrhh.models import AnexoContrato, Cargo, Contrato, Trabajador


@admin.register(Trabajador)
class TrabajadorAdmin(admin.ModelAdmin):
    list_display = ("nombre_completo", "rut", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre_completo", "rut", "rut_normalizado")
    readonly_fields = (
        "rut_normalizado",
        "creado_en",
        "actualizado_en",
    )


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


class AnexoContratoInline(admin.TabularInline):
    model = AnexoContrato
    extra = 0
    autocomplete_fields = ("nuevo_cargo", "nuevo_centro_costo")


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = (
        "trabajador",
        "cargo",
        "tipo_contrato",
        "fecha_inicio",
        "fecha_termino",
        "estado",
    )
    list_filter = ("estado", "tipo_contrato")
    search_fields = (
        "trabajador__nombre_completo",
        "trabajador__rut",
    )
    autocomplete_fields = ("trabajador", "cargo", "centro_costo")
    inlines = [AnexoContratoInline]


@admin.register(AnexoContrato)
class AnexoContratoAdmin(admin.ModelAdmin):
    list_display = (
        "contrato",
        "tipo",
        "fecha_vigencia",
        "fecha_documento",
    )
    list_filter = ("tipo",)
    autocomplete_fields = (
        "contrato",
        "nuevo_cargo",
        "nuevo_centro_costo",
    )
