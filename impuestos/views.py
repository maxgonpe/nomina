from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from impuestos.forms import PeriodoImpuestoForm
from impuestos.models import PeriodoImpuesto
from impuestos.services import cerrar_periodo, reabrir_periodo
from impuestos.forms_pagos import AnularPagoImpuestoForm, PagoImpuestoForm
from impuestos.models import PagoImpuesto
from impuestos.pagos import anular_pago, registrar_pago, situacion_pago


class PeriodoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "impuestos.view_periodoimpuesto"
    model = PeriodoImpuesto
    context_object_name = "periodos"
    template_name = "impuestos/periodos/lista.html"


class PeriodoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "impuestos.add_periodoimpuesto"
    model = PeriodoImpuesto
    form_class = PeriodoImpuestoForm
    template_name = "impuestos/periodos/form.html"
    success_url = "/impuestos/periodos/"


class PeriodoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "impuestos.view_periodoimpuesto"
    model = PeriodoImpuesto
    context_object_name = "periodo"
    template_name = "impuestos/periodos/detalle.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["situacion_pago"] = situacion_pago(self.object)
        return context


class PagoImpuestoCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "impuestos.add_pagoimpuesto"

    def get(self, request, pk):
        periodo = get_object_or_404(PeriodoImpuesto, pk=pk)
        return render(request, "impuestos/pagos/form.html", {"periodo": periodo, "form": PagoImpuestoForm()})

    def post(self, request, pk):
        periodo = get_object_or_404(PeriodoImpuesto, pk=pk)
        form = PagoImpuestoForm(request.POST, request.FILES)
        if form.is_valid():
            pago = form.save(commit=False)
            pago.periodo = periodo
            registrar_pago(pago)
            messages.success(request, "Pago registrado.")
            return redirect("impuestos:periodo_detalle", pk=pk)
        return render(request, "impuestos/pagos/form.html", {"periodo": periodo, "form": form})


class PagoImpuestoAnularView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "impuestos.change_pagoimpuesto"

    def get(self, request, pk):
        pago = get_object_or_404(PagoImpuesto, pk=pk)
        return render(request, "impuestos/pagos/anular.html", {"pago": pago, "form": AnularPagoImpuestoForm()})

    def post(self, request, pk):
        pago = get_object_or_404(PagoImpuesto, pk=pk)
        form = AnularPagoImpuestoForm(request.POST)
        if form.is_valid():
            anular_pago(pago, request.user, form.cleaned_data["motivo"])
            messages.success(request, "Pago anulado.")
            return redirect("impuestos:periodo_detalle", pk=pago.periodo_id)
        return render(request, "impuestos/pagos/anular.html", {"pago": pago, "form": form})


class PeriodoCerrarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "impuestos.change_periodoimpuesto"

    def post(self, request, pk):
        periodo = get_object_or_404(PeriodoImpuesto, pk=pk)
        cerrar_periodo(periodo, request.user)
        messages.success(request, "Período tributario cerrado.")
        return redirect("impuestos:periodo_detalle", pk=pk)


class PeriodoReabrirView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "impuestos.change_periodoimpuesto"

    def post(self, request, pk):
        periodo = get_object_or_404(PeriodoImpuesto, pk=pk)
        reabrir_periodo(periodo, request.user)
        messages.success(request, "Período tributario reabierto.")
        return redirect("impuestos:periodo_detalle", pk=pk)
