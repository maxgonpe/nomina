from django.urls import path

from rendiciones import views

app_name = "rendiciones"

urlpatterns = [
    path(
        "",
        views.RendicionListView.as_view(),
        name="rendicion_lista",
    ),
    path(
        "resumen/",
        views.ResumenRendicionesView.as_view(),
        name="rendicion_resumen",
    ),
    path(
        "nueva/",
        views.RendicionCreateView.as_view(),
        name="rendicion_crear",
    ),
    path(
        "<int:pk>/",
        views.RendicionDetailView.as_view(),
        name="rendicion_detalle",
    ),
    path(
        "<int:pk>/editar/",
        views.RendicionUpdateView.as_view(),
        name="rendicion_editar",
    ),
    path(
        "<int:pk>/distribucion/",
        views.RendicionDistribucionView.as_view(),
        name="rendicion_distribucion",
    ),
    path(
        "<int:pk>/anular/",
        views.RendicionAnularView.as_view(),
        name="rendicion_anular",
    ),
    path(
        "<int:pk>/presentar/",
        views.RendicionPresentarView.as_view(),
        name="rendicion_presentar",
    ),
    path(
        "<int:pk>/aprobar/",
        views.RendicionAprobarView.as_view(),
        name="rendicion_aprobar",
    ),
    path(
        "<int:pk>/rechazar/",
        views.RendicionRechazarView.as_view(),
        name="rendicion_rechazar",
    ),
    path(
        "<int:pk>/reabrir/",
        views.RendicionReabrirView.as_view(),
        name="rendicion_reabrir",
    ),
    path(
        "<int:pk>/documentos/agregar/",
        views.DocumentoRendicionCreateView.as_view(),
        name="documento_agregar",
    ),
    path(
        "documentos/<int:pk>/eliminar/",
        views.DocumentoRendicionDeleteView.as_view(),
        name="documento_eliminar",
    ),
]
