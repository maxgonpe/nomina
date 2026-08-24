from django.contrib import admin

from integracion_excel.models import (
    ExportacionExcel,
    ImportacionExcel,
    ImportacionFila,
    MapeoExcel,
    PlantillaExcel,
)


class MapeoExcelInline(admin.TabularInline):
    model = MapeoExcel
    extra = 0


@admin.register(PlantillaExcel)
class PlantillaExcelAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo", "version", "activo")
    list_filter = ("tipo", "activo")
    inlines = [MapeoExcelInline]


class ImportacionFilaInline(admin.TabularInline):
    model = ImportacionFila
    extra = 0


@admin.register(ImportacionExcel)
class ImportacionExcelAdmin(admin.ModelAdmin):
    list_display = ("id", "estado", "nombre_original")
    list_filter = ("estado",)
    inlines = [ImportacionFilaInline]


@admin.register(ExportacionExcel)
class ExportacionExcelAdmin(admin.ModelAdmin):
    list_display = ("id", "plantilla", "anio", "mes", "estado")
    list_filter = ("estado",)
