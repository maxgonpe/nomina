from django.urls import path

from balance import views

app_name = "balance"
urlpatterns = [
    path("lineas/", views.LineaBalanceListView.as_view(), name="linea_lista"),
    path("<int:anio>/", views.BalanceAnualView.as_view(), name="anual"),
]
