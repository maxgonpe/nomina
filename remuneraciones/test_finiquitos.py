from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import CentroCosto
from remuneraciones.models import (
    Finiquito,
    LiquidacionMensual,
    MovimientoRemuneracion,
)
from remuneraciones.services.finiquitos import (
    anular,
    registrar,
    sincronizar_movimiento_finiquito,
    suma_finiquitos,
    terminar_contrato_por_finiquito,
    validar,
)
from remuneraciones.services.periodos import (
    abrir,
    cerrar,
    crear,
    marcar_calculado,
    validar as validar_periodo,
)
from rrhh.models import Cargo, Contrato, Trabajador

User = get_user_model()


class Rem008Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rrhh", password="clave-segura")
        perms = Permission.objects.filter(
            content_type__app_label="remuneraciones",
            codename__in=[
                "view_finiquito",
                "add_finiquito",
                "change_finiquito",
                "delete_finiquito",
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

    def _fin(self, monto="500000", dia=20, **kwargs):
        return registrar(
            trabajador=self.trabajador,
            contrato=self.contrato,
            periodo=self.periodo,
            fecha=date(2026, 8, dia),
            monto=Decimal(str(monto)),
            motivo=Finiquito.Motivo.MUTUO_ACUERDO,
            usuario=self.user,
            **kwargs,
        )


class FiniquitoReglasTests(Rem008Base):
    def test_borrador_no_alimenta_liquidacion(self):
        fin = self._fin()
        self.assertEqual(fin.estado, Finiquito.Estado.BORRADOR)
        self.assertEqual(MovimientoRemuneracion.objects.count(), 0)
        self.assertEqual(
            suma_finiquitos(self.trabajador, self.periodo),
            Decimal("0.00"),
        )
        self.assertIsNone(self.contrato.fecha_termino)
        self.assertEqual(self.contrato.estado, Contrato.Estado.VIGENTE)

    def test_validar_crea_un_movimiento_finiquito(self):
        fin = self._fin("250000")
        validar(fin, usuario=self.user)
        movs = MovimientoRemuneracion.objects.filter(
            concepto__codigo="FINIQUITO"
        )
        self.assertEqual(movs.count(), 1)
        mov = movs.get()
        self.assertEqual(mov.monto, Decimal("250000.00"))
        self.assertEqual(mov.origen, MovimientoRemuneracion.Origen.CALCULADO)
        self.assertTrue(mov.bloqueado)
        self.assertTrue(mov.generado_automaticamente)
        self.assertEqual(
            suma_finiquitos(self.trabajador, self.periodo),
            Decimal("250000.00"),
        )
        fin.refresh_from_db()
        self.assertEqual(fin.liquidacion_id, mov.liquidacion_id)

    def test_recalculo_no_duplica_el_movimiento(self):
        fin = validar(self._fin("100000"), usuario=self.user)
        sincronizar_movimiento_finiquito(fin, usuario=self.user)
        sincronizar_movimiento_finiquito(fin, usuario=self.user)
        self.assertEqual(
            MovimientoRemuneracion.objects.filter(
                concepto__codigo="FINIQUITO"
            ).count(),
            1,
        )

    def test_validar_no_cierra_el_contrato(self):
        fin = validar(self._fin(), usuario=self.user)
        self.contrato.refresh_from_db()
        self.assertIsNone(self.contrato.fecha_termino)
        self.assertEqual(self.contrato.estado, Contrato.Estado.VIGENTE)
        terminar_contrato_por_finiquito(fin, usuario=self.user)
        self.contrato.refresh_from_db()
        self.assertEqual(self.contrato.fecha_termino, fin.fecha)
        self.assertEqual(self.contrato.estado, Contrato.Estado.TERMINADO)

    def test_anular_quita_el_movimiento_y_conserva_el_evento(self):
        fin = validar(self._fin("80000"), usuario=self.user)
        anular(fin, usuario=self.user)
        self.assertEqual(
            MovimientoRemuneracion.objects.filter(
                concepto__codigo="FINIQUITO"
            ).count(),
            0,
        )
        self.assertTrue(Finiquito.objects.filter(pk=fin.pk).exists())
        fin.refresh_from_db()
        self.assertEqual(fin.estado, Finiquito.Estado.ANULADO)
        self.assertEqual(
            suma_finiquitos(self.trabajador, self.periodo),
            Decimal("0.00"),
        )

    def test_fecha_fuera_del_periodo(self):
        with self.assertRaises(ValidationError):
            registrar(
                trabajador=self.trabajador,
                contrato=self.contrato,
                periodo=self.periodo,
                fecha=date(2026, 7, 31),
                monto=Decimal("1"),
                usuario=self.user,
            )

    def test_monto_positivo(self):
        with self.assertRaises(ValidationError):
            self._fin("0")

    def test_no_dos_activos_en_el_mismo_periodo(self):
        self._fin()
        with self.assertRaises(ValidationError):
            self._fin(dia=25)

    def test_guarda_archivo(self):
        archivo = SimpleUploadedFile(
            "finiquito.pdf",
            b"%PDF-1.4 test",
            content_type="application/pdf",
        )
        fin = self._fin(archivo=archivo)
        self.assertTrue(fin.archivo)
        self.assertIn("remuneraciones/finiquitos/2026/", fin.archivo.name)
        self.assertTrue(fin.archivo.name.endswith(".pdf"))

    def test_cerrado_no_crea(self):
        marcar_calculado(self.periodo, usuario=self.user)
        validar_periodo(self.periodo, usuario=self.user)
        LiquidacionMensual.objects.filter(periodo=self.periodo).update(
            estado=LiquidacionMensual.Estado.ANULADA,
            requiere_recalculo=False,
        )
        cerrar(self.periodo, usuario=self.user)
        self.periodo.refresh_from_db()
        with self.assertRaises(ValidationError):
            self._fin()


class FiniquitoVistaTests(Rem008Base):
    def test_lista_alta_y_validar(self):
        response = self.client.get(reverse("remuneraciones:finiquito_lista"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("remuneraciones:finiquito_crear"),
            {
                "trabajador": self.trabajador.pk,
                "contrato": self.contrato.pk,
                "periodo": self.periodo.pk,
                "fecha": "2026-08-20",
                "motivo": Finiquito.Motivo.RENUNCIA,
                "monto": "400000",
                "observaciones": "Término de faena EGC",
            },
        )
        self.assertEqual(Finiquito.objects.count(), 1)
        fin = Finiquito.objects.get()
        self.assertRedirects(
            response,
            reverse("remuneraciones:finiquito_detalle", args=[fin.pk]),
        )
        self.assertEqual(fin.estado, Finiquito.Estado.BORRADOR)
        self.assertEqual(MovimientoRemuneracion.objects.count(), 0)
        response = self.client.post(
            reverse("remuneraciones:finiquito_validar", args=[fin.pk])
        )
        self.assertRedirects(
            response,
            reverse("remuneraciones:finiquito_detalle", args=[fin.pk]),
        )
        self.assertEqual(
            MovimientoRemuneracion.objects.filter(
                concepto__codigo="FINIQUITO"
            ).count(),
            1,
        )
        self.client.post(
            reverse("remuneraciones:finiquito_validar", args=[fin.pk])
        )
        self.assertEqual(
            MovimientoRemuneracion.objects.filter(
                concepto__codigo="FINIQUITO"
            ).count(),
            1,
        )
