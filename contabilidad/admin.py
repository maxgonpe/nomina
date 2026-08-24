from django.contrib import admin

from contabilidad.models import AsientoContable, CuentaContable, DetalleAsiento


@admin.register(CuentaContable)
class CuentaContableAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo", "naturaleza", "activo")
    list_filter = ("tipo", "activo")
    search_fields = ("codigo", "nombre")


class DetalleAsientoInline(admin.TabularInline):
    model = DetalleAsiento
    extra = 0


@admin.register(AsientoContable)
class AsientoContableAdmin(admin.ModelAdmin):
    list_display = ("numero", "fecha", "glosa", "estado")
    list_filter = ("estado",)
    inlines = [DetalleAsientoInline]
