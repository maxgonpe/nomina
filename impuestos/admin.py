from django.contrib import admin

from impuestos.models import DetalleImpuesto, PagoImpuesto, PeriodoImpuesto


class DetalleImpuestoInline(admin.TabularInline):
    model = DetalleImpuesto
    extra = 0


@admin.register(PeriodoImpuesto)
class PeriodoImpuestoAdmin(admin.ModelAdmin):
    list_display = ("anio", "mes", "monto_a_pagar", "estado")
    list_filter = ("anio", "estado")
    inlines = [DetalleImpuestoInline]


@admin.register(PagoImpuesto)
class PagoImpuestoAdmin(admin.ModelAdmin):
    list_display = ("periodo", "fecha", "monto")
