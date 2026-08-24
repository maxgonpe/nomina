from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    UpdateView,
)

from core.mixins import AuditFormMixin
from core.validators import normalizar_rut
from rrhh.forms import TrabajadorForm
from rrhh.models import Trabajador
from rrhh.services.trabajadores import desactivar_trabajador


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
