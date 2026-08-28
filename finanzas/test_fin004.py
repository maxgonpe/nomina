from datetime import date
from django.test import TestCase
from facturacion.models import Proveedor, DocumentoCompra, PagoDocumentoCompra
from impuestos.models import PeriodoImpuesto, PagoImpuesto
from finanzas.models import MovimientoFinanciero
from finanzas.integracion_egresos import sincronizar_pagos_compras, sincronizar_pagos_impuestos

class FIN004Tests(TestCase):
    def test_compras_e_impuestos_generan_egresos_idempotentes(self):
        proveedor = Proveedor.objects.create(rut="18.651.495-5", razon_social="Proveedor FIN004")
        compra = DocumentoCompra.objects.create(proveedor=proveedor, fecha_documento=date(2026, 8, 1), tipo_documento="FACTURA", numero="F4", neto=100, iva=19, total=119)
        PagoDocumentoCompra.objects.create(documento=compra, fecha=date(2026, 8, 5), monto=119)
        periodo = PeriodoImpuesto.objects.create(anio=2026, mes=8, monto_a_pagar=50)
        PagoImpuesto.objects.create(periodo=periodo, fecha=date(2026, 8, 10), monto=50)
        sincronizar_pagos_compras(); sincronizar_pagos_impuestos(); sincronizar_pagos_compras(); sincronizar_pagos_impuestos()
        self.assertEqual(MovimientoFinanciero.objects.count(), 2)
