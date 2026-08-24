from django.contrib import admin

from rendiciones.models import DocumentoRendicion, Rendicion, RendicionDetalle


class RendicionDetalleInline(admin.TabularInline):
    model = RendicionDetalle
    extra = 0


@admin.register(Rendicion)
class RendicionAdmin(admin.ModelAdmin):
    list_display = ("id", "trabajador", "fecha", "total_declarado", "estado")
    list_filter = ("estado",)
    inlines = [RendicionDetalleInline]


@admin.register(DocumentoRendicion)
class DocumentoRendicionAdmin(admin.ModelAdmin):
    list_display = ("rendicion", "tipo")
