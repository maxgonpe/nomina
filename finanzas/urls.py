from django.urls import path
from finanzas import views

app_name = "finanzas"
urlpatterns = [
    path("movimientos/", views.MovimientoFinancieroListView.as_view(), name="movimiento_lista"),
    path("movimientos/nuevo/", views.MovimientoManualCreateView.as_view(), name="movimiento_manual_crear"),
    path("movimientos/<int:pk>/anular/", views.MovimientoManualAnularView.as_view(), name="movimiento_manual_anular"),
]
