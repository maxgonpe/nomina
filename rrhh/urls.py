from django.urls import path

from rrhh import views

app_name = "rrhh"

urlpatterns = [
    path(
        "trabajadores/",
        views.TrabajadorListView.as_view(),
        name="trabajador_lista",
    ),
    path(
        "trabajadores/nuevo/",
        views.TrabajadorCreateView.as_view(),
        name="trabajador_crear",
    ),
    path(
        "trabajadores/<int:pk>/",
        views.TrabajadorDetailView.as_view(),
        name="trabajador_detalle",
    ),
    path(
        "trabajadores/<int:pk>/editar/",
        views.TrabajadorUpdateView.as_view(),
        name="trabajador_editar",
    ),
    path(
        "trabajadores/<int:pk>/desactivar/",
        views.TrabajadorDesactivarView.as_view(),
        name="trabajador_desactivar",
    ),
]
