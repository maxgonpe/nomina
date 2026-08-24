from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    UpdateView,
)

from core.mixins import AuditFormMixin
from core.validators import normalizar_rut
from rrhh.forms import (
    AnexoContratoForm,
    CargoForm,
    ContratoForm,
    TrabajadorForm,
)
from rrhh.models import AnexoContrato, Cargo, Contrato, Trabajador
from rrhh.services.contratos import condicion_vigente
from rrhh.services.trabajadores import desactivar_trabajador


def _parse_fecha(valor, default=None):
    if not valor:
        return default
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return default


class TrabajadorListView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    ListView,
):
    permission_required = "rrhh.view_trabajador"
    model = Trabajador
    paginate_by = 25
    template_name = "rrhh/trabajadores/lista.html"
    context_object_name = "trabajadores"

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.GET.get("incluir_inactivos") != "1":
            qs = qs.filter(activo=True)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(nombre_completo__icontains=q)
                | Q(rut__icontains=q)
                | Q(rut_normalizado__icontains=normalizar_rut(q))
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "").strip()
        context["incluir_inactivos"] = (
            self.request.GET.get("incluir_inactivos") == "1"
        )
        return context


class TrabajadorCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    CreateView,
):
    permission_required = "rrhh.add_trabajador"
    model = Trabajador
    form_class = TrabajadorForm
    template_name = "rrhh/trabajadores/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Trabajador creado correctamente.")
        return super().form_valid(form)


class TrabajadorDetailView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    DetailView,
):
    permission_required = "rrhh.view_trabajador"
    model = Trabajador
    template_name = "rrhh/trabajadores/detalle.html"
    context_object_name = "trabajador"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fecha = _parse_fecha(
            self.request.GET.get("fecha"),
            default=timezone.localdate(),
        )
        context["fecha_consulta"] = fecha
        context["condicion"] = condicion_vigente(self.object, fecha)
        context["contratos"] = (
            self.object.contratos.select_related(
                "cargo",
                "centro_costo",
            )
            .prefetch_related("anexos")
        )
        return context


class TrabajadorUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    UpdateView,
):
    permission_required = "rrhh.change_trabajador"
    model = Trabajador
    form_class = TrabajadorForm
    template_name = "rrhh/trabajadores/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Trabajador actualizado.")
        return super().form_valid(form)


class TrabajadorDesactivarView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    View,
):
    permission_required = "rrhh.delete_trabajador"

    def get(self, request, pk):
        trabajador = get_object_or_404(Trabajador, pk=pk)
        return render(
            request,
            "rrhh/trabajadores/confirmar_desactivacion.html",
            {"trabajador": trabajador},
        )

    def post(self, request, pk):
        trabajador = get_object_or_404(Trabajador, pk=pk)
        if not trabajador.activo:
            messages.info(request, "El trabajador ya estaba inactivo.")
        else:
            desactivar_trabajador(trabajador, usuario=request.user)
            messages.success(
                request,
                f"{trabajador.nombre_completo} fue desactivado. "
                "El histórico se conserva.",
            )
        return redirect("rrhh:trabajador_detalle", pk=trabajador.pk)


class CargoListView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    ListView,
):
    permission_required = "rrhh.view_cargo"
    model = Cargo
    paginate_by = 25
    template_name = "rrhh/cargos/lista.html"
    context_object_name = "cargos"

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.GET.get("incluir_inactivos") != "1":
            qs = qs.filter(activo=True)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(codigo__icontains=q) | Q(nombre__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "").strip()
        context["incluir_inactivos"] = (
            self.request.GET.get("incluir_inactivos") == "1"
        )
        return context


class CargoCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    CreateView,
):
    permission_required = "rrhh.add_cargo"
    model = Cargo
    form_class = CargoForm
    template_name = "rrhh/cargos/form.html"
    success_url = None

    def form_valid(self, form):
        messages.success(self.request, "Cargo creado correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("rrhh:cargo_lista")


class CargoUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    UpdateView,
):
    permission_required = "rrhh.change_cargo"
    model = Cargo
    form_class = CargoForm
    template_name = "rrhh/cargos/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Cargo actualizado.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("rrhh:cargo_lista")


class ContratoListView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    ListView,
):
    permission_required = "rrhh.view_contrato"
    model = Contrato
    paginate_by = 25
    template_name = "rrhh/contratos/lista.html"
    context_object_name = "contratos"

    def get_queryset(self):
        qs = super().get_queryset().select_related(
            "trabajador",
            "cargo",
            "centro_costo",
        )
        trabajador_id = self.kwargs.get("trabajador_id")
        if trabajador_id:
            qs = qs.filter(trabajador_id=trabajador_id)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(trabajador__nombre_completo__icontains=q)
                | Q(trabajador__rut__icontains=q)
                | Q(cargo__nombre__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "").strip()
        context["trabajador"] = None
        trabajador_id = self.kwargs.get("trabajador_id")
        if trabajador_id:
            context["trabajador"] = get_object_or_404(
                Trabajador, pk=trabajador_id
            )
        return context


class ContratoCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    CreateView,
):
    permission_required = "rrhh.add_contrato"
    model = Contrato
    form_class = ContratoForm
    template_name = "rrhh/contratos/form.html"

    def dispatch(self, request, *args, **kwargs):
        self.trabajador = None
        trabajador_id = kwargs.get("trabajador_id")
        if trabajador_id:
            self.trabajador = get_object_or_404(Trabajador, pk=trabajador_id)
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if self.trabajador:
            initial["trabajador"] = self.trabajador
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.trabajador:
            form.fields["trabajador"].widget = form.fields["trabajador"].hidden_widget()
            form.initial["trabajador"] = self.trabajador.pk
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["trabajador"] = self.trabajador
        return context

    def form_valid(self, form):
        if self.trabajador:
            form.instance.trabajador = self.trabajador
        messages.success(self.request, "Contrato creado correctamente.")
        return super().form_valid(form)


class ContratoDetailView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    DetailView,
):
    permission_required = "rrhh.view_contrato"
    model = Contrato
    template_name = "rrhh/contratos/detalle.html"
    context_object_name = "contrato"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("trabajador", "cargo", "centro_costo")
            .prefetch_related("anexos__nuevo_cargo", "anexos__nuevo_centro_costo")
        )


class ContratoUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    UpdateView,
):
    permission_required = "rrhh.change_contrato"
    model = Contrato
    form_class = ContratoForm
    template_name = "rrhh/contratos/form.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["trabajador"].widget = form.fields["trabajador"].hidden_widget()
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["trabajador"] = self.object.trabajador
        return context

    def form_valid(self, form):
        messages.success(self.request, "Contrato actualizado.")
        return super().form_valid(form)


class AnexoContratoCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    CreateView,
):
    permission_required = "rrhh.add_anexocontrato"
    model = AnexoContrato
    form_class = AnexoContratoForm
    template_name = "rrhh/anexos/form.html"

    def dispatch(self, request, *args, **kwargs):
        self.contrato = get_object_or_404(Contrato, pk=kwargs["contrato_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contrato"] = self.contrato
        return context

    def form_valid(self, form):
        form.instance.contrato = self.contrato
        messages.success(self.request, "Anexo registrado correctamente.")
        return super().form_valid(form)


class AnexoContratoUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    UpdateView,
):
    permission_required = "rrhh.change_anexocontrato"
    model = AnexoContrato
    form_class = AnexoContratoForm
    template_name = "rrhh/anexos/form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contrato"] = self.object.contrato
        return context

    def form_valid(self, form):
        messages.success(self.request, "Anexo actualizado.")
        return super().form_valid(form)
