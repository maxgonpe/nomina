from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView

from balance.models import LineaBalance
from balance.anual import reporte_anual


class LineaBalanceListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "balance.view_lineabalance"
    model = LineaBalance
    context_object_name = "lineas"
    template_name = "balance/lineas_lista.html"

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.GET.get("incluir_inactivas") != "1":
            qs = qs.filter(activa=True)
        return qs


class BalanceAnualView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "balance.view_lineabalance"
    template_name = "balance/anual.html"
    context_object_name = "meses"

    def get_queryset(self):
        return reporte_anual(int(self.kwargs["anio"]))["meses"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["anio"] = int(self.kwargs["anio"])
        context["reporte"] = reporte_anual(context["anio"])
        return context
