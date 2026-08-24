from django.contrib import admin

from facturacion.models import (
    Cliente,
    CobroDocumentoTributario,
    DocumentoCompra,
    DocumentoTributario,
    Obra,
    PagoDocumentoCompra,
    Proveedor,
)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "rut", "activo")
    search_fields = ("razon_social", "rut")


@admin.register(Obra)
class ObraAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "cliente", "estado")
    list_filter = ("estado",)
    search_fields = ("codigo", "nombre")


@admin.register(DocumentoTributario)
class DocumentoTributarioAdmin(admin.ModelAdmin):
    list_display = (
        "tipo_documento",
        "numero",
        "cliente",
        "fecha_emision",
        "total",
        "estado",
    )
    list_filter = ("tipo_documento", "estado")


@admin.register(CobroDocumentoTributario)
class CobroDocumentoTributarioAdmin(admin.ModelAdmin):
    list_display = ("documento", "fecha", "monto")


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "rut", "activo")
    search_fields = ("razon_social", "rut")


@admin.register(DocumentoCompra)
class DocumentoCompraAdmin(admin.ModelAdmin):
    list_display = ("proveedor", "tipo_documento", "numero", "total", "estado")
    list_filter = ("estado",)


@admin.register(PagoDocumentoCompra)
class PagoDocumentoCompraAdmin(admin.ModelAdmin):
    list_display = ("documento", "fecha", "monto")
