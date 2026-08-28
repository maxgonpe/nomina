from django.urls import path
from impuestos import views

app_name = "impuestos"
urlpatterns = [
    path("periodos/", views.PeriodoListView.as_view(), name="periodo_lista"),
    path("periodos/nuevo/", views.PeriodoCreateView.as_view(), name="periodo_crear"),
    path("periodos/<int:pk>/", views.PeriodoDetailView.as_view(), name="periodo_detalle"),
    path("periodos/<int:pk>/cerrar/", views.PeriodoCerrarView.as_view(), name="periodo_cerrar"),
    path("periodos/<int:pk>/reabrir/", views.PeriodoReabrirView.as_view(), name="periodo_reabrir"),
    path("periodos/<int:pk>/pagos/nuevo/", views.PagoImpuestoCreateView.as_view(), name="pago_crear"),
    path("pagos/<int:pk>/anular/", views.PagoImpuestoAnularView.as_view(), name="pago_anular"),
]
