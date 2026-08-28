from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from finanzas.forms import AnularMovimientoManualForm, FiltroMovimientosFinancierosForm, MovimientoManualForm
from finanzas.models import MovimientoFinanciero
from finanzas.manuales import anular_movimiento_manual, registrar_movimiento_manual


class MovimientoFinancieroListView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "finanzas.view_movimientofinanciero"

    def get(self, request):
        form = FiltroMovimientosFinancierosForm(request.GET or None)
        movimientos = MovimientoFinanciero.objects.select_related("categoria", "centro_costo").order_by("-fecha", "-pk")
        if form.is_valid():
            filtros = form.cleaned_data
            if filtros.get("fecha_desde"):
                movimientos = movimientos.filter(fecha__gte=filtros["fecha_desde"])
            if filtros.get("fecha_hasta"):
                movimientos = movimientos.filter(fecha__lte=filtros["fecha_hasta"])
            for campo in ("tipo", "origen", "categoria"):
                if filtros.get(campo):
                    movimientos = movimientos.filter(**{campo: filtros[campo]})
            if filtros.get("estado") == "ANULADO":
                movimientos = movimientos.filter(anulado=True)
            elif filtros.get("estado") != "TODOS":
                movimientos = movimientos.filter(anulado=False)
        else:
            movimientos = movimientos.filter(anulado=False)
        return render(request, "finanzas/movimientos_lista.html", {"form": form, "movimientos": movimientos})


class MovimientoManualCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "finanzas.add_movimientofinanciero"

    def get(self, request):
        return render(request, "finanzas/movimiento_form.html", {"form": MovimientoManualForm()})

    def post(self, request):
        form = MovimientoManualForm(request.POST, request.FILES)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.origen = MovimientoFinanciero.Origen.MANUAL
            try:
                registrar_movimiento_manual(movimiento)
            except Exception as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, "Movimiento manual registrado.")
                return redirect("finanzas:movimiento_manual_crear")
        return render(request, "finanzas/movimiento_form.html", {"form": form})


class MovimientoManualAnularView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "finanzas.change_movimientofinanciero"

    def get(self, request, pk):
        movimiento = get_object_or_404(MovimientoFinanciero, pk=pk)
        return render(request, "finanzas/movimiento_anular.html", {"movimiento": movimiento, "form": AnularMovimientoManualForm()})

    def post(self, request, pk):
        movimiento = get_object_or_404(MovimientoFinanciero, pk=pk)
        form = AnularMovimientoManualForm(request.POST)
        if form.is_valid():
            anular_movimiento_manual(movimiento, request.user, form.cleaned_data["motivo"])
            messages.success(request, "Movimiento manual anulado.")
            return redirect("finanzas:movimiento_manual_crear")
        return render(request, "finanzas/movimiento_anular.html", {"movimiento": movimiento, "form": form})
