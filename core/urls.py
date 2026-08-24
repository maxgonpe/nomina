from django.urls import path

from core import views

app_name = "core"

urlpatterns = [
    path(
        "",
        views.ParametroListView.as_view(),
        name="parametro_lista",
    ),
    path(
        "nuevo/",
        views.ParametroCreateView.as_view(),
        name="parametro_crear",
    ),
    path(
        "<int:pk>/",
        views.ParametroDetailView.as_view(),
        name="parametro_detalle",
    ),
    path(
        "<int:pk>/editar/",
        views.ParametroUpdateView.as_view(),
        name="parametro_editar",
    ),
    path(
        "<int:parametro_id>/valores/nuevo/",
        views.ParametroValorCreateView.as_view(),
        name="parametro_valor_crear",
    ),
    path(
        "valores/<int:pk>/editar/",
        views.ParametroValorUpdateView.as_view(),
        name="parametro_valor_editar",
    ),
]
