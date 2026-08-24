"""
URL configuration for nomina project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

admin.site.site_header = "Nómina — Sistemas Hídricos"
admin.site.site_title = "Nómina"
admin.site.index_title = "Administración"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cuentas/", include("django.contrib.auth.urls")),
    path("rrhh/", include("rrhh.urls")),
    path(
        "",
        RedirectView.as_view(pattern_name="rrhh:trabajador_lista"),
        name="inicio",
    ),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
