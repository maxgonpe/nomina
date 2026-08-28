from django.urls import path

from facturacion import views

app_name = "facturacion"

urlpatterns = [
    path("clientes/", views.ClienteListView.as_view(), name="cliente_lista"),
    path("clientes/nuevo/", views.ClienteCreateView.as_view(), name="cliente_crear"),
    path("clientes/<int:pk>/", views.ClienteDetailView.as_view(), name="cliente_detalle"),
    path("clientes/<int:pk>/editar/", views.ClienteUpdateView.as_view(), name="cliente_editar"),
    path("clientes/<int:pk>/desactivar/", views.ClienteDesactivarView.as_view(), name="cliente_desactivar"),
    path("proveedores/", views.ProveedorListView.as_view(), name="proveedor_lista"),
    path("proveedores/nuevo/", views.ProveedorCreateView.as_view(), name="proveedor_crear"),
    path("proveedores/<int:pk>/", views.ProveedorDetailView.as_view(), name="proveedor_detalle"),
    path("proveedores/<int:pk>/editar/", views.ProveedorUpdateView.as_view(), name="proveedor_editar"),
    path("proveedores/<int:pk>/desactivar/", views.ProveedorDesactivarView.as_view(), name="proveedor_desactivar"),
    path("compras/", views.DocumentoCompraListView.as_view(), name="compra_lista"),
    path("compras/resumen/", views.ResumenComprasView.as_view(), name="compras_resumen"),
    path("compras/nueva/", views.DocumentoCompraCreateView.as_view(), name="compra_crear"),
    path("compras/<int:pk>/", views.DocumentoCompraDetailView.as_view(), name="compra_detalle"),
    path("compras/<int:pk>/editar/", views.DocumentoCompraUpdateView.as_view(), name="compra_editar"),
    path("compras/<int:pk>/anular/", views.DocumentoCompraAnularView.as_view(), name="compra_anular"),
    path("proveedores/<int:proveedor_id>/compras/", views.DocumentoCompraListView.as_view(), name="proveedor_compras"),
    path("compras/<int:documento_id>/pagos/nuevo/", views.PagoDocumentoCompraCreateView.as_view(), name="pago_compra_crear"),
    path("compras/pagos/<int:pk>/anular/", views.PagoDocumentoCompraAnularView.as_view(), name="pago_compra_anular"),
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
    path("cobros/<int:pk>/anular/", views.CobroDocumentoAnularView.as_view(), name="cobro_anular"),
    path("resumen/", views.ResumenFacturacionView.as_view(), name="resumen"),
]
