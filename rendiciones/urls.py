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
        "<int:pk>/anular/",
        views.RendicionAnularView.as_view(),
        name="rendicion_anular",
    ),
]
