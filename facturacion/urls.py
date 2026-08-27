from django.urls import path

from facturacion import views

app_name = "facturacion"

urlpatterns = [
    path("clientes/", views.ClienteListView.as_view(), name="cliente_lista"),
    path("clientes/nuevo/", views.ClienteCreateView.as_view(), name="cliente_crear"),
    path("clientes/<int:pk>/", views.ClienteDetailView.as_view(), name="cliente_detalle"),
    path("clientes/<int:pk>/editar/", views.ClienteUpdateView.as_view(), name="cliente_editar"),
    path("clientes/<int:pk>/desactivar/", views.ClienteDesactivarView.as_view(), name="cliente_desactivar"),
    path("obras/", views.ObraListView.as_view(), name="obra_lista"),
    path("obras/nueva/", views.ObraCreateView.as_view(), name="obra_crear"),
    path("obras/<int:pk>/", views.ObraDetailView.as_view(), name="obra_detalle"),
    path("obras/<int:pk>/editar/", views.ObraUpdateView.as_view(), name="obra_editar"),
    path("clientes/<int:cliente_id>/obras/", views.ObraListView.as_view(), name="cliente_obras"),
    path("clientes/<int:cliente_id>/obras/nueva/", views.ObraCreateView.as_view(), name="cliente_obra_crear"),
    path("documentos/", views.DocumentoTributarioListView.as_view(), name="documento_lista"),
    path("documentos/nuevo/", views.DocumentoTributarioCreateView.as_view(), name="documento_crear"),
    path("documentos/<int:pk>/", views.DocumentoTributarioDetailView.as_view(), name="documento_detalle"),
    path("documentos/<int:pk>/editar/", views.DocumentoTributarioUpdateView.as_view(), name="documento_editar"),
    path("documentos/<int:pk>/anular/", views.DocumentoTributarioAnularView.as_view(), name="documento_anular"),
    path("clientes/<int:cliente_id>/documentos/", views.DocumentoTributarioListView.as_view(), name="cliente_documentos"),
    path("obras/<int:obra_id>/documentos/", views.DocumentoTributarioListView.as_view(), name="obra_documentos"),
    path("documentos/<int:documento_id>/cobros/nuevo/", views.CobroDocumentoCreateView.as_view(), name="cobro_crear"),
    path("cobros/<int:pk>/editar/", views.CobroDocumentoUpdateView.as_view(), name="cobro_editar"),
    path("resumen/", views.ResumenFacturacionView.as_view(), name="resumen"),
]
