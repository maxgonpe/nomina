from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import CentroCosto
from remuneraciones.models import (
    ConceptoRemuneracion,
    LiquidacionMensual,
    MovimientoRemuneracion,
    PeriodoRemuneracion,
)
from remuneraciones.services.movimientos import (
    registrar_movimiento,
    suma_movimientos,
)
from remuneraciones.services.periodos import (
    abrir,
    cerrar,
    crear,
    marcar_calculado,
    validar,
)
from rrhh.models import Cargo, Contrato, Trabajador

User = get_user_model()


class Rem007Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rrhh", password="clave-segura")
        perms = Permission.objects.filter(
            content_type__app_label="remuneraciones",
            codename__in=[
                "view_movimientoremuneracion",
                "add_movimientoremuneracion",
                "change_movimientoremuneracion",
                "delete_movimientoremuneracion",
                "view_periodoremuneracion",
                "change_periodoremuneracion",
            ],
        )
        extra = Permission.objects.filter(
            content_type__app_label="rrhh",
            codename="view_trabajador",
        )
        self.user.user_permissions.set(list(perms) + list(extra))
        self.client.force_login(self.user)
        self.trabajador = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        self.cargo = Cargo.objects.create(codigo="MAESTRO", nombre="Maestro")
        self.cc = CentroCosto.objects.create(
            codigo="EGC",
            nombre="Edificio Gran Costanera",
            tipo=CentroCosto.Tipo.OBRA,
        )
        self.contrato = Contrato.objects.create(
            trabajador=self.trabajador,
            cargo=self.cargo,
            centro_costo=self.cc,
            fecha_inicio=date(2026, 1, 1),
            sueldo_base_inicial=Decimal("800000"),
        )
        self.periodo = crear(anio=2026, mes=8, usuario=self.user)
        abrir(self.periodo, usuario=self.user)
        self.aguinaldo = ConceptoRemuneracion.objects.get(codigo="AGUINALDO")
        self.anticipo = ConceptoRemuneracion.objects.get(codigo="ANTICIPO")
        self.prestamo_desc = ConceptoRemuneracion.objects.get(
            codigo="PRESTAMO_DESCUENTO"
        )
        self.prestamo_ent = ConceptoRemuneracion.objects.get(
            codigo="PRESTAMO_ENTREGADO"
        )

    def _mov(self, concepto, monto, **kwargs):
        return registrar_movimiento(
            trabajador=self.trabajador,
            periodo=self.periodo,
            concepto=concepto,
            monto=Decimal(str(monto)),
            usuario=self.user,
            **kwargs,
        )


class MovimientoReglasTests(Rem007Base):
    def test_signo_lo_define_el_tipo_del_concepto(self):
        haber = self._mov(self.aguinaldo, "100000")
        descuento = self._mov(self.anticipo, "100000")
        self.assertEqual(haber.monto, Decimal("100000.00"))
        self.assertEqual(descuento.monto, Decimal("100000.00"))
        self.assertEqual(haber.monto_con_signo, Decimal("100000.00"))
        self.assertEqual(descuento.monto_con_signo, Decimal("-100000.00"))
        self.assertEqual(
            suma_movimientos(
                self.trabajador,
                self.periodo,
                tipo=ConceptoRemuneracion.Tipo.HABER,
            ),
            Decimal("100000.00"),
        )
        self.assertEqual(
            suma_movimientos(
                self.trabajador,
                self.periodo,
                tipo=ConceptoRemuneracion.Tipo.DESCUENTO,
            ),
            Decimal("100000.00"),
        )

    def test_prestamo_no_se_asume_por_el_nombre(self):
        self.assertEqual(
            self.prestamo_ent.tipo, ConceptoRemuneracion.Tipo.HABER
        )
        self.assertEqual(
            self.prestamo_desc.tipo, ConceptoRemuneracion.Tipo.DESCUENTO
        )
        entrega = self._mov(self.prestamo_ent, "80000")
        cuota = self._mov(self.prestamo_desc, "80000")
        self.assertGreater(entrega.monto_con_signo, 0)
        self.assertLess(cuota.monto_con_signo, 0)

    def test_nuevo_concepto_no_altera_liquidacion(self):
        campos_antes = {f.name for f in LiquidacionMensual._meta.get_fields()}
        bono = ConceptoRemuneracion.objects.create(
            codigo="BONO_FAENA",
            nombre="Bono faena",
            tipo=ConceptoRemuneracion.Tipo.HABER,
        )
        self._mov(bono, "150000")
        campos_despues = {f.name for f in LiquidacionMensual._meta.get_fields()}
        self.assertEqual(campos_antes, campos_despues)
        self.assertTrue(
            MovimientoRemuneracion.objects.filter(concepto=bono).exists()
        )
        self.assertFalse(
            any("bono" in nombre for nombre in campos_despues)
        )

    def test_crea_liquidacion_borrador_si_no_existe(self):
        self.assertEqual(LiquidacionMensual.objects.count(), 0)
        self._mov(self.aguinaldo, "50000")
        liq = LiquidacionMensual.objects.get()
        self.assertEqual(liq.estado, LiquidacionMensual.Estado.BORRADOR)
        self.assertEqual(liq.contrato, self.contrato)
        self.assertTrue(liq.requiere_recalculo)

    def test_origen_manual_por_defecto(self):
        mov = self._mov(self.aguinaldo, "10000")
        self.assertEqual(mov.origen, MovimientoRemuneracion.Origen.MANUAL)
        self.assertFalse(mov.generado_automaticamente)

    def test_no_permite_sueldo_base_a_mano(self):
        sueldo = ConceptoRemuneracion.objects.get(codigo="SUELDO_BASE")
        with self.assertRaises(ValidationError):
            self._mov(sueldo, "800000")

    def test_monto_debe_ser_positivo(self):
        with self.assertRaises(ValidationError):
            self._mov(self.aguinaldo, "0")
        with self.assertRaises(ValidationError):
            self._mov(self.aguinaldo, "-10000")

    def test_modificar_marca_liquidacion_pendiente(self):
        mov = self._mov(self.aguinaldo, "10000")
        liq = mov.liquidacion
        LiquidacionMensual.objects.filter(pk=liq.pk).update(
            estado=LiquidacionMensual.Estado.CALCULADA,
            requiere_recalculo=False,
        )
        registrar_movimiento(
            trabajador=self.trabajador,
            periodo=self.periodo,
            concepto=self.aguinaldo,
            monto=Decimal("20000"),
            usuario=self.user,
            instance=mov,
        )
        liq.refresh_from_db()
        self.assertTrue(liq.requiere_recalculo)

    def test_bloqueado_no_se_edita_ni_borra(self):
        mov = self._mov(self.aguinaldo, "10000")
        MovimientoRemuneracion.objects.filter(pk=mov.pk).update(bloqueado=True)
        mov.refresh_from_db()
        with self.assertRaises(ValidationError):
            registrar_movimiento(
                trabajador=self.trabajador,
                periodo=self.periodo,
                concepto=self.aguinaldo,
                monto=Decimal("1"),
                usuario=self.user,
                instance=mov,
            )
        mov.refresh_from_db()
        with self.assertRaises(ValidationError):
            mov.delete()

    def test_cerrado_no_crea_ni_borra(self):
        mov = self._mov(self.aguinaldo, "10000")
        marcar_calculado(self.periodo, usuario=self.user)
        validar(self.periodo, usuario=self.user)
        LiquidacionMensual.objects.filter(periodo=self.periodo).update(
            estado=LiquidacionMensual.Estado.ANULADA,
            requiere_recalculo=False,
        )
        cerrar(self.periodo, usuario=self.user)
        self.periodo.refresh_from_db()
        with self.assertRaises(ValidationError):
            self._mov(self.anticipo, "5000")
        mov = MovimientoRemuneracion.objects.get(pk=mov.pk)
        with self.assertRaises(ValidationError):
            mov.delete()


class MovimientoVistaTests(Rem007Base):
    def test_lista_y_alta(self):
        response = self.client.get(reverse("remuneraciones:movimiento_lista"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("remuneraciones:movimiento_crear"),
            {
                "trabajador": self.trabajador.pk,
                "periodo": self.periodo.pk,
                "concepto": self.aguinaldo.pk,
                "monto": "100000",
                "descripcion": "Fiestas patrias",
            },
        )
        self.assertEqual(MovimientoRemuneracion.objects.count(), 1)
        mov = MovimientoRemuneracion.objects.get()
        self.assertEqual(mov.concepto, self.aguinaldo)
        self.assertEqual(mov.origen, MovimientoRemuneracion.Origen.MANUAL)
        self.assertEqual(mov.monto_con_signo, Decimal("100000.00"))

    def test_carga_rapida_en_periodo_sin_salir(self):
        url = reverse(
            "remuneraciones:periodo_movimientos",
            args=[self.periodo.pk],
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            url,
            {
                "mov-TOTAL_FORMS": "3",
                "mov-INITIAL_FORMS": "0",
                "mov-MIN_NUM_FORMS": "0",
                "mov-MAX_NUM_FORMS": "1000",
                "mov-0-trabajador": str(self.trabajador.pk),
                "mov-0-concepto": str(self.aguinaldo.pk),
                "mov-0-monto": "100000",
                "mov-0-descripcion": "Aguinaldo",
                "mov-1-trabajador": str(self.trabajador.pk),
                "mov-1-concepto": str(self.anticipo.pk),
                "mov-1-monto": "50000",
                "mov-1-descripcion": "Anticipo quincena",
                "mov-2-trabajador": "",
                "mov-2-concepto": "",
                "mov-2-monto": "",
                "mov-2-descripcion": "",
            },
        )
        self.assertRedirects(response, url)
        self.assertEqual(MovimientoRemuneracion.objects.count(), 2)
        self.assertEqual(
            suma_movimientos(
                self.trabajador,
                self.periodo,
                tipo=ConceptoRemuneracion.Tipo.HABER,
            ),
            Decimal("100000.00"),
        )
        self.assertEqual(
            suma_movimientos(
                self.trabajador,
                self.periodo,
                tipo=ConceptoRemuneracion.Tipo.DESCUENTO,
            ),
            Decimal("50000.00"),
        )
