from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from core.mixins import AuditFormMixin
from remuneraciones.forms import (
    ConceptoRemuneracionForm,
    HoraExtraCargaRapidaFormSet,
    HoraExtraForm,
    PeriodoForm,
    ReaperturaPeriodoForm,
)
from remuneraciones.models import (
    ConceptoRemuneracion,
    HoraExtra,
    PeriodoRemuneracion,
)
from remuneraciones.services.horas_extra import (
    suma_horas_extra,
    totales_horas_extra_por_trabajador,
)
from remuneraciones.services.periodos import (
    acciones_disponibles,
    abrir,
    cerrar,
    marcar_calculado,
    reabrir,
    validar,
)
from rrhh.models import Trabajador


def _mensaje_error(exc):
    if hasattr(exc, "messages"):
        return " ".join(str(m) for m in exc.messages)
    return str(exc)


class PeriodoListView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    ListView,
):
    permission_required = "remuneraciones.view_periodoremuneracion"
    model = PeriodoRemuneracion
    paginate_by = 24
    template_name = "remuneraciones/periodos/lista.html"
    context_object_name = "periodos"

    def get_queryset(self):
        qs = super().get_queryset()
        anio = self.request.GET.get("anio", "").strip()
        estado = self.request.GET.get("estado", "").strip()
        if anio.isdigit():
            qs = qs.filter(anio=int(anio))
        if estado:
            qs = qs.filter(estado=estado)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["anio"] = self.request.GET.get("anio", "").strip()
        context["estado"] = self.request.GET.get("estado", "").strip()
        context["estados"] = PeriodoRemuneracion.Estado.choices
        anios = list(
            PeriodoRemuneracion.objects.order_by("-anio")
            .values_list("anio", flat=True)
            .distinct()
        )
        actual = timezone.localdate().year
        if actual not in anios:
            anios.insert(0, actual)
        context["anios"] = anios
        return context


class PeriodoCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    CreateView,
):
    permission_required = "remuneraciones.add_periodoremuneracion"
    model = PeriodoRemuneracion
    form_class = PeriodoForm
    template_name = "remuneraciones/periodos/form.html"

    def form_valid(self, form):
        form.instance.estado = PeriodoRemuneracion.Estado.BORRADOR
        messages.success(
            self.request,
            "Período creado en borrador. La hoja Excel equivalente no lo abre.",
        )
        return super().form_valid(form)


class PeriodoDetailView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    DetailView,
):
    permission_required = "remuneraciones.view_periodoremuneracion"
    model = PeriodoRemuneracion
    template_name = "remuneraciones/periodos/detalle.html"
    context_object_name = "periodo"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["acciones"] = acciones_disponibles(self.object)
        context["liquidaciones"] = self.object.liquidaciones.select_related(
            "trabajador"
        )
        return context


class PeriodoUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    UpdateView,
):
    permission_required = "remuneraciones.change_periodoremuneracion"
    model = PeriodoRemuneracion
    form_class = PeriodoForm
    template_name = "remuneraciones/periodos/form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not self.has_permission():
            return self.handle_no_permission()
        periodo = get_object_or_404(PeriodoRemuneracion, pk=kwargs["pk"])
        if periodo.esta_cerrado:
            messages.error(
                request,
                "Un período cerrado no se edita. Use la reapertura autorizada.",
            )
            return redirect(periodo)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Período actualizado.")
        return super().form_valid(form)


class _PeriodoAccionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = "remuneraciones.change_periodoremuneracion"
    http_method_names = ["post"]

    def post(self, request, pk):
        periodo = get_object_or_404(PeriodoRemuneracion, pk=pk)
        try:
            self.ejecutar(periodo, request.user)
            messages.success(request, self.mensaje_ok(periodo))
        except ValidationError as exc:
            messages.error(request, _mensaje_error(exc))
        return redirect("remuneraciones:periodo_detalle", pk=periodo.pk)

    def ejecutar(self, periodo, usuario):
        raise NotImplementedError

    def mensaje_ok(self, periodo):
        raise NotImplementedError


class PeriodoAbrirView(_PeriodoAccionMixin, View):
    def ejecutar(self, periodo, usuario):
        abrir(periodo, usuario=usuario)

    def mensaje_ok(self, periodo):
        return f"{periodo.nombre} quedó abierto."


class PeriodoCalcularView(_PeriodoAccionMixin, View):
    def ejecutar(self, periodo, usuario):
        marcar_calculado(periodo, usuario=usuario)

    def mensaje_ok(self, periodo):
        return (
            f"{periodo.nombre} marcado como calculado. "
            "El motor de liquidación (REM005) usará este estado más adelante."
        )


class PeriodoValidarView(_PeriodoAccionMixin, View):
    def ejecutar(self, periodo, usuario):
        validar(periodo, usuario=usuario)

    def mensaje_ok(self, periodo):
        return f"{periodo.nombre} quedó validado."


class PeriodoCerrarView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    View,
):
    permission_required = "remuneraciones.change_periodoremuneracion"

    def get(self, request, pk):
        periodo = get_object_or_404(PeriodoRemuneracion, pk=pk)
        return render(
            request,
            "remuneraciones/periodos/cerrar.html",
            {
                "periodo": periodo,
                "acciones": acciones_disponibles(periodo),
            },
        )

    def post(self, request, pk):
        periodo = get_object_or_404(PeriodoRemuneracion, pk=pk)
        try:
            cerrar(periodo, usuario=request.user)
            messages.success(
                request,
                f"{periodo.nombre} cerrado. Ya no se pueden modificar "
                "horas extra, movimientos, liquidaciones ni finiquitos.",
            )
        except ValidationError as exc:
            messages.error(request, _mensaje_error(exc))
        return redirect("remuneraciones:periodo_detalle", pk=periodo.pk)


class PeriodoReabrirView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    View,
):
    permission_required = "remuneraciones.change_periodoremuneracion"

    def get(self, request, pk):
        periodo = get_object_or_404(PeriodoRemuneracion, pk=pk)
        return render(
            request,
            "remuneraciones/periodos/reabrir.html",
            {
                "periodo": periodo,
                "form": ReaperturaPeriodoForm(),
            },
        )

    def post(self, request, pk):
        periodo = get_object_or_404(PeriodoRemuneracion, pk=pk)
        form = ReaperturaPeriodoForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "remuneraciones/periodos/reabrir.html",
                {"periodo": periodo, "form": form},
            )
        try:
            reabrir(
                periodo,
                motivo=form.cleaned_data["motivo"],
                usuario=request.user,
            )
            messages.success(
                request,
                f"{periodo.nombre} reabierto. El motivo quedó en auditoría.",
            )
            return redirect("remuneraciones:periodo_detalle", pk=periodo.pk)
        except ValidationError as exc:
            form.add_error(None, _mensaje_error(exc))
            return render(
                request,
                "remuneraciones/periodos/reabrir.html",
                {"periodo": periodo, "form": form},
            )


class ConceptoListView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    ListView,
):
    permission_required = "remuneraciones.view_conceptoremuneracion"
    model = ConceptoRemuneracion
    paginate_by = 50
    template_name = "remuneraciones/conceptos/lista.html"
    context_object_name = "conceptos"

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.GET.get("incluir_inactivos") != "1":
            qs = qs.filter(activo=True)
        tipo = self.request.GET.get("tipo", "").strip()
        if tipo:
            qs = qs.filter(tipo=tipo)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(codigo__icontains=q) | Q(nombre__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "").strip()
        context["tipo"] = self.request.GET.get("tipo", "").strip()
        context["tipos"] = ConceptoRemuneracion.Tipo.choices
        context["incluir_inactivos"] = (
            self.request.GET.get("incluir_inactivos") == "1"
        )
        return context


class ConceptoCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    CreateView,
):
    permission_required = "remuneraciones.add_conceptoremuneracion"
    model = ConceptoRemuneracion
    form_class = ConceptoRemuneracionForm
    template_name = "remuneraciones/conceptos/form.html"

    def form_valid(self, form):
        messages.success(
            self.request,
            "Concepto creado. No se modificó la tabla de liquidaciones.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("remuneraciones:concepto_lista")


class ConceptoUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    UpdateView,
):
    permission_required = "remuneraciones.change_conceptoremuneracion"
    model = ConceptoRemuneracion
    form_class = ConceptoRemuneracionForm
    template_name = "remuneraciones/conceptos/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Concepto actualizado.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("remuneraciones:concepto_lista")


class HoraExtraListView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    ListView,
):
    permission_required = "remuneraciones.view_horaextra"
    model = HoraExtra
    paginate_by = 50
    template_name = "remuneraciones/horas_extra/lista.html"
    context_object_name = "horas_extra"

    def get_queryset(self):
        qs = super().get_queryset().select_related(
            "trabajador",
            "periodo",
        )
        trabajador_id = self.kwargs.get("trabajador_id") or self.request.GET.get(
            "trabajador"
        )
        periodo_id = self.kwargs.get("periodo_id") or self.request.GET.get(
            "periodo"
        )
        fecha = self.request.GET.get("fecha", "").strip()
        if trabajador_id:
            qs = qs.filter(trabajador_id=trabajador_id)
        if periodo_id:
            qs = qs.filter(periodo_id=periodo_id)
        if fecha:
            qs = qs.filter(fecha=fecha)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q_trabajador"] = str(
            self.kwargs.get("trabajador_id")
            or self.request.GET.get("trabajador")
            or ""
        )
        context["q_periodo"] = str(
            self.kwargs.get("periodo_id")
            or self.request.GET.get("periodo")
            or ""
        )
        context["q_fecha"] = self.request.GET.get("fecha", "").strip()
        context["trabajadores"] = Trabajador.objects.filter(
            activo=True
        ).order_by("nombre_completo")
        context["periodos"] = PeriodoRemuneracion.objects.all()
        context["trabajador"] = None
        context["periodo"] = None
        trabajador_id = self.kwargs.get("trabajador_id")
        periodo_id = self.kwargs.get("periodo_id")
        if trabajador_id:
            context["trabajador"] = get_object_or_404(
                Trabajador, pk=trabajador_id
            )
        if periodo_id:
            context["periodo"] = get_object_or_404(
                PeriodoRemuneracion, pk=periodo_id
            )
            context["totales"] = totales_horas_extra_por_trabajador(
                context["periodo"]
            )
        if context["trabajador"] and context["periodo"]:
            context["suma"] = suma_horas_extra(
                context["trabajador"],
                context["periodo"],
            )
        return context


class HoraExtraCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    CreateView,
):
    permission_required = "remuneraciones.add_horaextra"
    model = HoraExtra
    form_class = HoraExtraForm
    template_name = "remuneraciones/horas_extra/form.html"

    def dispatch(self, request, *args, **kwargs):
        self.periodo = None
        self.trabajador = None
        if kwargs.get("periodo_id"):
            self.periodo = get_object_or_404(
                PeriodoRemuneracion, pk=kwargs["periodo_id"]
            )
        if kwargs.get("trabajador_id"):
            self.trabajador = get_object_or_404(
                Trabajador, pk=kwargs["trabajador_id"]
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["periodo"] = self.periodo
        kwargs["trabajador"] = self.trabajador
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["periodo"] = self.periodo
        context["trabajador"] = self.trabajador
        return context

    def form_valid(self, form):
        messages.success(self.request, "Hora extra registrada.")
        return super().form_valid(form)

    def get_success_url(self):
        if self.periodo:
            return reverse(
                "remuneraciones:periodo_horas_extra",
                args=[self.periodo.pk],
            )
        if self.trabajador:
            return reverse(
                "remuneraciones:trabajador_horas_extra",
                args=[self.trabajador.pk],
            )
        return reverse("remuneraciones:hora_extra_lista")


class HoraExtraUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    UpdateView,
):
    permission_required = "remuneraciones.change_horaextra"
    model = HoraExtra
    form_class = HoraExtraForm
    template_name = "remuneraciones/horas_extra/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["periodo"] = self.object.periodo
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["periodo"] = self.object.periodo
        context["trabajador"] = self.object.trabajador
        return context

    def form_valid(self, form):
        messages.success(self.request, "Hora extra actualizada.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "remuneraciones:periodo_horas_extra",
            args=[self.object.periodo_id],
        )


class HoraExtraDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    DeleteView,
):
    permission_required = "remuneraciones.delete_horaextra"
    model = HoraExtra
    template_name = "remuneraciones/horas_extra/confirmar_borrar.html"

    def form_valid(self, form):
        periodo_id = self.object.periodo_id
        try:
            self.object.delete()
        except ValidationError as exc:
            messages.error(self.request, _mensaje_error(exc))
            return redirect(
                "remuneraciones:periodo_horas_extra",
                periodo_id=periodo_id,
            )
        messages.success(self.request, "Hora extra eliminada.")
        return redirect(
            "remuneraciones:periodo_horas_extra",
            periodo_id=periodo_id,
        )


class PeriodoHorasExtraView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    View,
):
    permission_required = "remuneraciones.view_horaextra"

    def dispatch(self, request, *args, **kwargs):
        self.periodo = get_object_or_404(
            PeriodoRemuneracion, pk=kwargs["periodo_id"]
        )
        return super().dispatch(request, *args, **kwargs)

    def _formset(self, data=None):
        return HoraExtraCargaRapidaFormSet(
            data=data,
            queryset=HoraExtra.objects.none(),
            form_kwargs={"periodo": self.periodo},
            prefix="he",
        )

    def get(self, request, periodo_id):
        return self._render(self._formset())

    def post(self, request, periodo_id):
        if not request.user.has_perm("remuneraciones.add_horaextra"):
            messages.error(
                request,
                "No tiene permiso para registrar horas extra.",
            )
            return redirect(
                "remuneraciones:periodo_horas_extra",
                periodo_id=self.periodo.pk,
            )
        if self.periodo.esta_cerrado:
            messages.error(
                request,
                "El período está cerrado. No se pueden registrar horas extra.",
            )
            return redirect(
                "remuneraciones:periodo_horas_extra",
                periodo_id=self.periodo.pk,
            )
        formset = self._formset(data=request.POST)
        if not formset.is_valid():
            return self._render(formset)
        creados = 0
        try:
            for form in formset:
                if not form.has_changed():
                    continue
                obj = form.save(commit=False)
                obj.periodo = self.periodo
                obj.origen = HoraExtra.Origen.MANUAL
                obj.creado_por = request.user
                obj.actualizado_por = request.user
                obj.full_clean()
                obj.save()
                creados += 1
        except ValidationError as exc:
            messages.error(request, _mensaje_error(exc))
            return self._render(formset)
        if creados:
            messages.success(
                request,
                f"Se registraron {creados} hora(s) extra. "
                "La liquidación, si existe, queda pendiente de recálculo.",
            )
        else:
            messages.info(request, "No se ingresó ninguna fila.")
        return redirect(
            "remuneraciones:periodo_horas_extra",
            periodo_id=self.periodo.pk,
        )

    def _render(self, formset):
        registros = (
            HoraExtra.objects.filter(periodo=self.periodo)
            .select_related("trabajador")
        )
        return render(
            self.request,
            "remuneraciones/horas_extra/periodo.html",
            {
                "periodo": self.periodo,
                "formset": formset,
                "horas_extra": registros,
                "totales": totales_horas_extra_por_trabajador(self.periodo),
                "puede_cargar": (
                    not self.periodo.esta_cerrado
                    and self.request.user.has_perm(
                        "remuneraciones.add_horaextra"
                    )
                ),
            },
        )
