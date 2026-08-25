from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    UpdateView,
)

from django.utils import timezone

from core.mixins import AuditFormMixin
from rendiciones.forms import (
    AnularRendicionForm,
    DocumentoRendicionForm,
    FiltroRendicionForm,
    RechazarRendicionForm,
    RendicionDetalleFormSet,
    RendicionForm,
)
from rendiciones.models import DocumentoRendicion, Rendicion
from rendiciones.services.estados import (
    acciones_disponibles,
    anular,
    aprobar,
    presentar,
    reabrir,
    rechazar,
)
from rendiciones.services.rendiciones import (
    eliminar_documento,
    guardar_distribucion,
    puede_editar,
    puede_editar_documentos,
    validar_cuadratura,
)
from rendiciones.services.reportes import (
    ESTADOS_OFICIALES,
    anios_disponibles,
    filtrar_rendiciones,
    resumen_por_centro,
)
from rrhh.models import Trabajador

class RendicionListView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    ListView,
):
    permission_required = "rendiciones.view_rendicion"
    model = Rendicion
    paginate_by = 25
    template_name = "rendiciones/rendicion_list.html"
    context_object_name = "rendiciones"

    def get_filtro_form(self):
        return FiltroRendicionForm(self.request.GET or None)

    def get_queryset(self):
        form = self.get_filtro_form()
        qs = Rendicion.objects.select_related("trabajador")
        if form.is_valid():
            data = form.cleaned_data
            estados = [data["estado"]] if data.get("estado") else None
            qs = filtrar_rendiciones(
                qs,
                anio=data.get("anio"),
                mes=data.get("mes"),
                fecha=data.get("fecha"),
                trabajador_id=(
                    data["trabajador"].pk if data.get("trabajador") else None
                ),
                centro_costo_id=(
                    data["centro_costo"].pk if data.get("centro_costo") else None
                ),
                estados=estados,
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.get_filtro_form()
        context["filtro_form"] = form
        context["estados"] = Rendicion.Estado.choices
        # querystring para paginación
        params = self.request.GET.copy()
        params.pop("page", None)
        context["filtro_qs"] = params.urlencode()
        return context


class ResumenRendicionesView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    View,
):
    """REN006 — totales por centro / trabajador (reporte)."""

    permission_required = "rendiciones.view_rendicion"
    template_name = "rendiciones/resumen.html"

    def get(self, request):
        form = FiltroRendicionForm(request.GET or None)
        anio = None
        mes = None
        trabajador_id = None
        centro_id = None
        if form.is_valid():
            data = form.cleaned_data
            anio = data.get("anio")
            mes = data.get("mes")
            if data.get("trabajador"):
                trabajador_id = data["trabajador"].pk
            if data.get("centro_costo"):
                centro_id = data["centro_costo"].pk
        if anio is None and not request.GET:
            anio = timezone.localdate().year

        # Estado del resumen: GET estados= o estado=; default oficiales
        estados_param = request.GET.get("estados", "").strip()
        estado_uno = request.GET.get("estado", "").strip()
        if estados_param:
            estados = [p.strip() for p in estados_param.split(",") if p.strip()]
        elif estado_uno:
            estados = [estado_uno]
        else:
            estados = list(ESTADOS_OFICIALES)

        resumen = resumen_por_centro(
            anio=anio,
            mes=mes,
            trabajador_id=trabajador_id,
            centro_costo_id=centro_id,
            estados=estados,
        )
        anios = list(anios_disponibles())
        if anio and anio not in anios:
            anios = sorted(set(anios + [anio]), reverse=True)

        return render(
            request,
            self.template_name,
            {
                "filtro_form": form,
                "resumen": resumen,
                "anios": anios,
                "estados_oficiales": ESTADOS_OFICIALES,
                "usar_oficiales": set(estados) == set(ESTADOS_OFICIALES),
            },
        )


class RendicionCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    CreateView,
):
    permission_required = "rendiciones.add_rendicion"
    model = Rendicion
    form_class = RendicionForm
    template_name = "rendiciones/rendicion_form.html"

    def form_valid(self, form):
        form.instance.estado = Rendicion.Estado.BORRADOR
        messages.success(self.request, "Rendición creada correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("rendiciones:rendicion_detalle", args=[self.object.pk])


class RendicionDetailView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    DetailView,
):
    permission_required = "rendiciones.view_rendicion"
    model = Rendicion
    template_name = "rendiciones/rendicion_detail.html"
    context_object_name = "rendicion"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "trabajador",
                "creado_por",
                "actualizado_por",
            )
            .prefetch_related("detalles__centro_costo", "documentos")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        acciones = acciones_disponibles(self.object)
        context["acciones"] = acciones
        context["puede_editar"] = acciones["editar"]
        context["puede_editar_documentos"] = puede_editar_documentos(self.object)
        context["puede_presentar"] = acciones["presentar"]
        context["puede_aprobar"] = acciones["aprobar"]
        context["puede_rechazar"] = acciones["rechazar"]
        context["puede_reabrir"] = acciones["reabrir"]
        context["puede_anular"] = acciones["anular"]
        context["detalles"] = self.object.detalles.select_related("centro_costo")
        context["documentos"] = self.object.documentos.all()
        try:
            validar_cuadratura(self.object)
            context["cuadratura_ok"] = True
            context["cuadratura_errores"] = []
        except ValidationError as exc:
            context["cuadratura_ok"] = False
            context["cuadratura_errores"] = list(exc.messages)
        return context


class RendicionDistribucionView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    View,
):
    permission_required = "rendiciones.change_rendicion"

    def dispatch(self, request, *args, **kwargs):
        self.rendicion = get_object_or_404(
            Rendicion.objects.select_related("trabajador"),
            pk=kwargs["pk"],
        )
        if not puede_editar(self.rendicion):
            messages.error(
                request,
                "Solo se puede distribuir una rendición en borrador.",
            )
            return redirect(
                "rendiciones:rendicion_detalle",
                pk=self.rendicion.pk,
            )
        return super().dispatch(request, *args, **kwargs)

    def _formset(self, data=None):
        return RendicionDetalleFormSet(
            data=data,
            instance=self.rendicion,
            queryset=self.rendicion.detalles.select_related("centro_costo"),
            prefix="det",
        )

    def get(self, request, pk):
        return self._render(self._formset())

    def post(self, request, pk):
        formset = self._formset(data=request.POST)
        try:
            guardar_distribucion(
                self.rendicion,
                formset,
                usuario=request.user,
            )
        except ValidationError as exc:
            if formset.errors or formset.non_form_errors():
                return self._render(formset)
            messages.error(request, "; ".join(exc.messages))
            return self._render(formset)
        messages.success(request, "Distribución guardada.")
        return redirect("rendiciones:rendicion_detalle", pk=self.rendicion.pk)

    def _render(self, formset):
        return render(
            request=self.request,
            template_name="rendiciones/rendicion_distribucion.html",
            context={
                "rendicion": self.rendicion,
                "formset": formset,
                "total_declarado": self.rendicion.total_declarado,
            },
        )


class RendicionUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    UpdateView,
):
    permission_required = "rendiciones.change_rendicion"
    model = Rendicion
    form_class = RendicionForm
    template_name = "rendiciones/rendicion_form.html"

    def dispatch(self, request, *args, **kwargs):
        rendicion = get_object_or_404(Rendicion, pk=kwargs["pk"])
        if not puede_editar(rendicion):
            messages.error(
                request,
                "Solo se pueden editar rendiciones en borrador.",
            )
            return redirect("rendiciones:rendicion_detalle", pk=rendicion.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # El estado no se edita en REN001; se conserva el vigente.
        messages.success(self.request, "Rendición actualizada.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("rendiciones:rendicion_detalle", args=[self.object.pk])


class RendicionAnularView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    View,
):
    permission_required = "rendiciones.anular_rendicion"

    def get(self, request, pk):
        rendicion = get_object_or_404(
            Rendicion.objects.select_related("trabajador"),
            pk=pk,
        )
        form = AnularRendicionForm()
        return render(
            request,
            "rendiciones/rendicion_anular.html",
            {
                "rendicion": rendicion,
                "form": form,
                "puede_anular": acciones_disponibles(rendicion)["anular"],
            },
        )

    def post(self, request, pk):
        rendicion = get_object_or_404(Rendicion, pk=pk)
        form = AnularRendicionForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "rendiciones/rendicion_anular.html",
                {
                    "rendicion": rendicion,
                    "form": form,
                    "puede_anular": acciones_disponibles(rendicion)["anular"],
                },
            )
        try:
            anular(
                rendicion,
                motivo=form.cleaned_data["motivo"],
                usuario=request.user,
            )
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
            return redirect("rendiciones:rendicion_detalle", pk=pk)
        messages.success(request, f"Rendición #{pk} anulada.")
        return redirect("rendiciones:rendicion_detalle", pk=pk)


class RendicionPresentarView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    View,
):
    """Confirmación (GET) + cambio de estado solo por POST (REN003/REN005)."""

    permission_required = "rendiciones.presentar_rendicion"

    def get(self, request, pk):
        rendicion = get_object_or_404(
            Rendicion.objects.select_related("trabajador"),
            pk=pk,
        )
        errores = []
        try:
            if rendicion.estado != Rendicion.Estado.BORRADOR:
                raise ValidationError(
                    "Solo una rendición en borrador puede presentarse."
                )
            validar_cuadratura(rendicion)
            cuadra = True
        except ValidationError as exc:
            cuadra = False
            errores = list(exc.messages)
        return render(
            request,
            "rendiciones/rendicion_presentar.html",
            {
                "rendicion": rendicion,
                "cuadra": cuadra,
                "errores": errores,
            },
        )

    def post(self, request, pk):
        rendicion = get_object_or_404(Rendicion, pk=pk)
        try:
            presentar(rendicion, usuario=request.user)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
            return redirect("rendiciones:rendicion_presentar", pk=pk)
        messages.success(
            request,
            f"Rendición #{pk} presentada. Queda pendiente de aprobación.",
        )
        return redirect("rendiciones:rendicion_detalle", pk=pk)


class RendicionAprobarView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    View,
):
    permission_required = "rendiciones.aprobar_rendicion"

    def get(self, request, pk):
        rendicion = get_object_or_404(
            Rendicion.objects.select_related("trabajador"),
            pk=pk,
        )
        return render(
            request,
            "rendiciones/rendicion_aprobar.html",
            {
                "rendicion": rendicion,
                "puede_aprobar": acciones_disponibles(rendicion)["aprobar"],
            },
        )

    def post(self, request, pk):
        rendicion = get_object_or_404(Rendicion, pk=pk)
        try:
            aprobar(rendicion, usuario=request.user)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
            return redirect("rendiciones:rendicion_detalle", pk=pk)
        messages.success(request, f"Rendición #{pk} aprobada.")
        return redirect("rendiciones:rendicion_detalle", pk=pk)


class RendicionRechazarView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    View,
):
    permission_required = "rendiciones.rechazar_rendicion"

    def get(self, request, pk):
        rendicion = get_object_or_404(
            Rendicion.objects.select_related("trabajador"),
            pk=pk,
        )
        return render(
            request,
            "rendiciones/rendicion_rechazar.html",
            {
                "rendicion": rendicion,
                "form": RechazarRendicionForm(),
                "puede_rechazar": acciones_disponibles(rendicion)["rechazar"],
            },
        )

    def post(self, request, pk):
        rendicion = get_object_or_404(Rendicion, pk=pk)
        form = RechazarRendicionForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "rendiciones/rendicion_rechazar.html",
                {
                    "rendicion": rendicion,
                    "form": form,
                    "puede_rechazar": acciones_disponibles(rendicion)["rechazar"],
                },
            )
        try:
            rechazar(
                rendicion,
                motivo=form.cleaned_data["motivo"],
                usuario=request.user,
            )
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
            return redirect("rendiciones:rendicion_detalle", pk=pk)
        messages.success(request, f"Rendición #{pk} rechazada.")
        return redirect("rendiciones:rendicion_detalle", pk=pk)


class RendicionReabrirView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    View,
):
    permission_required = "rendiciones.change_rendicion"

    def get(self, request, pk):
        rendicion = get_object_or_404(
            Rendicion.objects.select_related("trabajador"),
            pk=pk,
        )
        return render(
            request,
            "rendiciones/rendicion_reabrir.html",
            {
                "rendicion": rendicion,
                "puede_reabrir": acciones_disponibles(rendicion)["reabrir"],
            },
        )

    def post(self, request, pk):
        rendicion = get_object_or_404(Rendicion, pk=pk)
        try:
            reabrir(rendicion, usuario=request.user)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
            return redirect("rendiciones:rendicion_detalle", pk=pk)
        messages.success(
            request,
            f"Rendición #{pk} reabierta como borrador.",
        )
        return redirect("rendiciones:rendicion_detalle", pk=pk)


class DocumentoRendicionCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuditFormMixin,
    CreateView,
):
    permission_required = "rendiciones.add_documentorendicion"
    model = DocumentoRendicion
    form_class = DocumentoRendicionForm
    template_name = "rendiciones/documento_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.rendicion = get_object_or_404(
            Rendicion.objects.select_related("trabajador"),
            pk=kwargs["pk"],
        )
        if not puede_editar_documentos(self.rendicion):
            messages.error(
                request,
                "No se pueden agregar documentos en este estado.",
            )
            return redirect(
                "rendiciones:rendicion_detalle",
                pk=self.rendicion.pk,
            )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.rendicion = self.rendicion
        messages.success(self.request, "Documento adjuntado.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["rendicion"] = self.rendicion
        return context

    def get_success_url(self):
        return reverse(
            "rendiciones:rendicion_detalle",
            args=[self.rendicion.pk],
        )


class DocumentoRendicionDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    View,
):
    permission_required = "rendiciones.delete_documentorendicion"

    def get(self, request, pk):
        documento = get_object_or_404(
            DocumentoRendicion.objects.select_related(
                "rendicion",
                "rendicion__trabajador",
            ),
            pk=pk,
        )
        return render(
            request,
            "rendiciones/documento_confirm_delete.html",
            {
                "documento": documento,
                "rendicion": documento.rendicion,
                "puede_eliminar": puede_editar_documentos(documento.rendicion),
            },
        )

    def post(self, request, pk):
        documento = get_object_or_404(
            DocumentoRendicion.objects.select_related("rendicion"),
            pk=pk,
        )
        rendicion_id = documento.rendicion_id
        try:
            eliminar_documento(documento, usuario=request.user)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
            return redirect("rendiciones:rendicion_detalle", pk=rendicion_id)
        messages.success(request, "Documento eliminado.")
        return redirect("rendiciones:rendicion_detalle", pk=rendicion_id)
