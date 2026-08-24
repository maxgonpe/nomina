from django.contrib import admin

from remuneraciones.models import (
    ConceptoCostoTrabajador,
    ConceptoRemuneracion,
    CostoTrabajadorDetalle,
    CostoTrabajadorPeriodo,
    Finiquito,
    HoraExtra,
    LiquidacionMensual,
    MovimientoRemuneracion,
    PagoRemuneracion,
    PeriodoRemuneracion,
)


@admin.register(PeriodoRemuneracion)
class PeriodoRemuneracionAdmin(admin.ModelAdmin):
    list_display = ("anio", "mes", "estado")
    list_filter = ("anio", "estado")


@admin.register(ConceptoRemuneracion)
class ConceptoRemuneracionAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo", "activo", "orden")
    list_filter = ("tipo", "activo")
    search_fields = ("codigo", "nombre")


class MovimientoInline(admin.TabularInline):
    model = MovimientoRemuneracion
    extra = 0


@admin.register(LiquidacionMensual)
class LiquidacionMensualAdmin(admin.ModelAdmin):
    list_display = (
        "trabajador",
        "periodo",
        "estado",
        "total_a_pagar",
    )
    list_filter = ("estado", "periodo")
    search_fields = (
        "trabajador__nombre_completo",
        "trabajador__rut",
    )
    inlines = [MovimientoInline]


@admin.register(HoraExtra)
class HoraExtraAdmin(admin.ModelAdmin):
    list_display = ("trabajador", "periodo", "fecha", "horas")
    list_filter = ("periodo",)
    search_fields = ("trabajador__nombre_completo",)


@admin.register(PagoRemuneracion)
class PagoRemuneracionAdmin(admin.ModelAdmin):
    list_display = ("liquidacion", "fecha", "monto", "medio_pago")
    list_filter = ("medio_pago",)


@admin.register(Finiquito)
class FiniquitoAdmin(admin.ModelAdmin):
    list_display = ("trabajador", "fecha", "monto", "estado")
    list_filter = ("estado",)


@admin.register(ConceptoCostoTrabajador)
class ConceptoCostoTrabajadorAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo", "orden")


class CostoDetalleInline(admin.TabularInline):
    model = CostoTrabajadorDetalle
    extra = 0


@admin.register(CostoTrabajadorPeriodo)
class CostoTrabajadorPeriodoAdmin(admin.ModelAdmin):
    list_display = ("liquidacion", "total")
    inlines = [CostoDetalleInline]
