from datetime import date
from decimal import Decimal
from django.test import TestCase
from core.models import CentroCosto
from facturacion.models import DocumentoCompra, PagoDocumentoCompra, Proveedor
from facturacion.services.integracion_compras import documentos_para_impuestos, filas_exportacion_pagos_compras, pagos_para_finanzas


class COM006RTests(TestCase):
    def setUp(self):
        self.proveedor = Proveedor.objects.create(rut="18.651.495-5", razon_social="Proveedor integración")
        self.cc = CentroCosto.objects.create(codigo="CC-INT", nombre="Integración")
        self.documento = DocumentoCompra.objects.create(proveedor=self.proveedor, centro_costo=self.cc, fecha_documento=date(2026, 8, 15), tipo_documento="FACTURA", numero="1", neto=100, iva=19, total=119)

    def test_documento_para_impuestos_no_depende_del_pago(self):
        salida = documentos_para_impuestos(date(2026, 8, 1), date(2026, 8, 31))
        self.assertEqual(salida[0]["total"], Decimal("119"))
        self.assertEqual(salida[0]["tasa_iva_snapshot"], self.documento.tasa_iva_snapshot)

    def test_pago_usa_fecha_pago_y_conserva_origen(self):
        pago = PagoDocumentoCompra.objects.create(documento=self.documento, fecha=date(2026, 9, 5), monto=119)
        self.assertEqual(pagos_para_finanzas(date(2026, 8, 1), date(2026, 8, 31)), [])
        salida = pagos_para_finanzas(date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual(salida[0]["pago_id"], pago.pk)
        self.assertEqual(salida[0]["centro_costo"], self.cc)
        self.assertEqual(salida[0]["clave_origen"], f"COMPRA_PAGO:{pago.pk}")

    def test_pago_anulado_no_se_exporta(self):
        PagoDocumentoCompra.objects.create(documento=self.documento, fecha=date(2026, 9, 5), monto=119, anulado=True)
        self.assertEqual(filas_exportacion_pagos_compras(), [])
