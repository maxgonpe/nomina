from django.contrib import admin

from finanzas.models import (
    CategoriaFinanciera,
    CierreFinancieroMensual,
    MovimientoFinanciero,
    ObligacionFinanciera,
    PagoObligacionFinanciera,
)


@admin.register(CategoriaFinanciera)
class CategoriaFinancieraAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo", "activo")
    list_filter = ("tipo", "activo")
    search_fields = ("codigo", "nombre")


@admin.register(MovimientoFinanciero)
class MovimientoFinancieroAdmin(admin.ModelAdmin):
    list_display = ("fecha", "tipo", "categoria", "monto", "origen")
    list_filter = ("tipo", "origen")


@admin.register(CierreFinancieroMensual)
class CierreFinancieroMensualAdmin(admin.ModelAdmin):
    list_display = ("anio", "mes", "saldo_final", "estado")
    list_filter = ("anio", "estado")


@admin.register(ObligacionFinanciera)
class ObligacionFinancieraAdmin(admin.ModelAdmin):
    list_display = ("descripcion", "monto_total", "estado")
    list_filter = ("estado",)


@admin.register(PagoObligacionFinanciera)
class PagoObligacionFinancieraAdmin(admin.ModelAdmin):
    list_display = ("obligacion", "fecha", "monto")
