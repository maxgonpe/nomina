from datetime import date
from decimal import Decimal
from django.test import TestCase
from core.models import CentroCosto
from finanzas.models import CategoriaFinanciera, MovimientoFinanciero
from finanzas.integracion_remuneraciones import sincronizar_pagos_remuneracion
from remuneraciones.models import LiquidacionMensual, PagoRemuneracion, PeriodoRemuneracion
from rrhh.models import Cargo, Contrato, Trabajador

class FIN002Tests(TestCase):
    def test_pago_vigente_genera_un_movimiento_idempotente(self):
        trabajador = Trabajador.objects.create(rut="18.651.495-5", nombre_completo="Ana Pérez")
        cargo = Cargo.objects.create(codigo="ANALISTA", nombre="Analista")
        centro = CentroCosto.objects.create(codigo="CC-FIN", nombre="Finanzas")
        contrato = Contrato.objects.create(trabajador=trabajador, cargo=cargo, centro_costo=centro, fecha_inicio=date(2026, 1, 1), sueldo_base_inicial=1000)
        periodo = PeriodoRemuneracion.objects.create(anio=2026, mes=8)
        liquidacion = LiquidacionMensual.objects.create(trabajador=trabajador, periodo=periodo, contrato=contrato, centro_costo=centro, sueldo_base_snapshot=1000, total_haberes=1000, total_descuentos=0, total_a_pagar=1000)
        pago = PagoRemuneracion.objects.create(liquidacion=liquidacion, fecha=date(2026, 8, 31), monto=1000)
        movimientos = sincronizar_pagos_remuneracion()
        sincronizar_pagos_remuneracion()
        self.assertEqual(len(movimientos), 1)
        self.assertEqual(MovimientoFinanciero.objects.count(), 1)
        self.assertEqual(MovimientoFinanciero.objects.get().categoria.codigo, "EGR_REMUNERACIONES")
