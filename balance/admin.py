from django.contrib import admin

from balance.models import CierreBalance, LineaBalance


@admin.register(LineaBalance)
class LineaBalanceAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "seccion", "fuente", "activa", "permite_ajuste")
    list_filter = ("seccion", "fuente", "activa")
    search_fields = ("codigo", "nombre")


@admin.register(CierreBalance)
class CierreBalanceAdmin(admin.ModelAdmin):
    list_display = ("fecha_corte", "estado", "caja", "resultado", "posicion_disponible")
    list_filter = ("estado",)
    readonly_fields = ("fecha_corte", "caja", "cuentas_por_cobrar", "obligaciones", "resultado", "posicion_disponible", "resumen_fuentes")
