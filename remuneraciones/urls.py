from django.urls import path

from remuneraciones import views

app_name = "remuneraciones"

urlpatterns = [
    path(
        "periodos/",
        views.PeriodoListView.as_view(),
        name="periodo_lista",
    ),
    path(
        "periodos/nuevo/",
        views.PeriodoCreateView.as_view(),
        name="periodo_crear",
    ),
    path(
        "periodos/<int:pk>/",
        views.PeriodoDetailView.as_view(),
        name="periodo_detalle",
    ),
    path(
        "periodos/<int:pk>/editar/",
        views.PeriodoUpdateView.as_view(),
        name="periodo_editar",
    ),
    path(
        "periodos/<int:pk>/abrir/",
        views.PeriodoAbrirView.as_view(),
        name="periodo_abrir",
    ),
    path(
        "periodos/<int:pk>/calcular/",
        views.PeriodoCalcularView.as_view(),
        name="periodo_calcular",
    ),
    path(
        "periodos/<int:pk>/validar/",
        views.PeriodoValidarView.as_view(),
        name="periodo_validar",
    ),
    path(
        "periodos/<int:pk>/cerrar/",
        views.PeriodoCerrarView.as_view(),
        name="periodo_cerrar",
    ),
    path(
        "periodos/<int:pk>/reabrir/",
        views.PeriodoReabrirView.as_view(),
        name="periodo_reabrir",
    ),
]
