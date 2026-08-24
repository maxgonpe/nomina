from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    UpdateView,
)

from core.forms import ParametroNegocioForm, ParametroValorForm
from core.mixins import AuditFormMixin
from core.models import ParametroNegocio, ParametroValor


class ParametroListView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    ListView,
):
    permission_required = "core.view_parametronegocio"
    model = ParametroNegocio
    paginate_by = 50
    template_name = "core/parametros/lista.html"
    context_object_name = "parametros"

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.GET.get("incluir_inactivos") != "1":
            qs = qs.filter(activo=True)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(codigo__icontains=q) | Q(nombre__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "").strip()
        context["incluir_inactivos"] = (
            self.request.GET.get("incluir_inactivos") == "1"
        )
        return context


class ParametroCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    CreateView,
):
    permission_required = "core.add_parametronegocio"
    model = ParametroNegocio
    form_class = ParametroNegocioForm
    template_name = "core/parametros/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Parámetro creado.")
        return super().form_valid(form)


class ParametroDetailView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    DetailView,
):
    permission_required = "core.view_parametronegocio"
    model = ParametroNegocio
    template_name = "core/parametros/detalle.html"
    context_object_name = "parametro"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["valores"] = self.object.valores.all()
        return context


class ParametroUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    UpdateView,
):
    permission_required = "core.change_parametronegocio"
    model = ParametroNegocio
    form_class = ParametroNegocioForm
    template_name = "core/parametros/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Parámetro actualizado.")
        return super().form_valid(form)


class ParametroValorCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    CreateView,
):
    permission_required = "core.add_parametrovalor"
    model = ParametroValor
    form_class = ParametroValorForm
    template_name = "core/parametros/valor_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.parametro = get_object_or_404(
            ParametroNegocio, pk=kwargs["parametro_id"]
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.instance.parametro = self.parametro
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parametro"] = self.parametro
        return context

    def form_valid(self, form):
        form.instance.parametro = self.parametro
        messages.success(self.request, "Vigencia registrada.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("core:parametro_detalle", args=[self.parametro.pk])


class ParametroValorUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    UpdateView,
):
    permission_required = "core.change_parametrovalor"
    model = ParametroValor
    form_class = ParametroValorForm
    template_name = "core/parametros/valor_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parametro"] = self.object.parametro
        return context

    def form_valid(self, form):
        messages.success(self.request, "Vigencia actualizada.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "core:parametro_detalle", args=[self.object.parametro_id]
        )
