from datetime import date
from decimal import Decimal
from django.test import TestCase
from facturacion.models import Cliente, CobroDocumentoTributario, DocumentoTributario
from finanzas.models import MovimientoFinanciero
from finanzas.integracion_facturacion import sincronizar_cobros

class FIN003Tests(TestCase):
    def test_cobro_usa_fecha_real_y_no_duplica(self):
        cliente = Cliente.objects.create(rut="18.651.495-5", razon_social="Cliente cobro")
        documento = DocumentoTributario.objects.create(fecha_emision=date(2026, 8, 1), cliente=cliente, tipo_documento="FACTURA", numero="FIN3", neto=100, iva=19, total=119)
        cobro = CobroDocumentoTributario.objects.create(documento=documento, fecha=date(2026, 9, 5), monto=119, referencia="TR-1")
        sincronizar_cobros(date(2026, 9, 1), date(2026, 9, 30))
        sincronizar_cobros(date(2026, 9, 1), date(2026, 9, 30))
        movimiento = MovimientoFinanciero.objects.get()
        self.assertEqual(movimiento.fecha, date(2026, 9, 5))
        self.assertEqual(movimiento.monto, Decimal("119"))
        self.assertEqual(MovimientoFinanciero.objects.count(), 1)

    def test_cobro_anulado_no_genera_ingreso(self):
        cliente = Cliente.objects.create(rut="18.651.495-5", razon_social="Cliente cobro 2")
        documento = DocumentoTributario.objects.create(fecha_emision=date(2026, 8, 1), cliente=cliente, tipo_documento="FACTURA", numero="FIN3-2", neto=100, iva=19, total=119)
        CobroDocumentoTributario.objects.create(documento=documento, fecha=date(2026, 9, 5), monto=119, anulado=True)
        self.assertEqual(sincronizar_cobros(), [])
