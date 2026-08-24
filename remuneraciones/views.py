from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    UpdateView,
)

from core.mixins import AuditFormMixin
from remuneraciones.forms import PeriodoForm, ReaperturaPeriodoForm
from remuneraciones.models import PeriodoRemuneracion
from remuneraciones.services.periodos import (
    acciones_disponibles,
    abrir,
    cerrar,
    marcar_calculado,
    reabrir,
    validar,
)


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
