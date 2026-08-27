from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.mixins import AuditFormMixin
from core.validators import normalizar_rut
from facturacion.forms import AnularDocumentoTributarioForm, ClienteForm, DocumentoTributarioForm, ObraForm
from facturacion.models import Cliente, DocumentoTributario, Obra


class ClienteListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "facturacion.view_cliente"
    model = Cliente
    context_object_name = "clientes"
    template_name = "facturacion/clientes/lista.html"
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.GET.get("incluir_inactivos") != "1":
            queryset = queryset.filter(activo=True)
        consulta = self.request.GET.get("q", "").strip()
        if consulta:
            queryset = queryset.filter(
                Q(razon_social__icontains=consulta)
                | Q(rut__icontains=consulta)
                | Q(rut_normalizado__icontains=normalizar_rut(consulta))
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "").strip()
        context["incluir_inactivos"] = self.request.GET.get("incluir_inactivos") == "1"
        return context


class ClienteCreateView(LoginRequiredMixin, PermissionRequiredMixin, AuditFormMixin, CreateView):
    permission_required = "facturacion.add_cliente"
    model = Cliente
    form_class = ClienteForm
    template_name = "facturacion/clientes/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Cliente creado correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("facturacion:cliente_detalle", args=[self.object.pk])


class ClienteDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "facturacion.view_cliente"
    model = Cliente
    context_object_name = "cliente"
    template_name = "facturacion/clientes/detalle.html"


class ClienteUpdateView(LoginRequiredMixin, PermissionRequiredMixin, AuditFormMixin, UpdateView):
    permission_required = "facturacion.change_cliente"
    model = Cliente
    form_class = ClienteForm
    template_name = "facturacion/clientes/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Cliente actualizado.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("facturacion:cliente_detalle", args=[self.object.pk])


class ClienteDesactivarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "facturacion.delete_cliente"

    def get(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        return render(request, "facturacion/clientes/confirmar_desactivacion.html", {"cliente": cliente})

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        if cliente.activo:
            cliente.activo = False
            cliente.actualizado_por = request.user
            cliente.save(update_fields=["activo", "actualizado_por", "actualizado_en"])
            messages.success(request, "Cliente desactivado. El histórico se conserva.")
        else:
            messages.info(request, "El cliente ya estaba inactivo.")
        return redirect("facturacion:cliente_detalle", pk=cliente.pk)


class ObraListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "facturacion.view_obra"
    model = Obra
    context_object_name = "obras"
    template_name = "facturacion/obras/lista.html"
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related("cliente", "centro_costo")
        cliente_id = self.kwargs.get("cliente_id") or self.request.GET.get("cliente")
        if cliente_id:
            queryset = queryset.filter(cliente_id=cliente_id)
        estado = self.request.GET.get("estado", "")
        if estado:
            queryset = queryset.filter(estado=estado)
        consulta = self.request.GET.get("q", "").strip()
        if consulta:
            queryset = queryset.filter(Q(codigo__icontains=consulta) | Q(nombre__icontains=consulta))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "").strip()
        context["estado"] = self.request.GET.get("estado", "")
        context["estados"] = Obra.Estado.choices
        context["cliente"] = get_object_or_404(Cliente, pk=self.kwargs["cliente_id"]) if self.kwargs.get("cliente_id") else None
        return context


class ObraCreateView(LoginRequiredMixin, PermissionRequiredMixin, AuditFormMixin, CreateView):
    permission_required = "facturacion.add_obra"
    model = Obra
    form_class = ObraForm
    template_name = "facturacion/obras/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.kwargs.get("cliente_id"):
            kwargs["cliente"] = get_object_or_404(Cliente, pk=self.kwargs["cliente_id"])
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Obra creada correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("facturacion:obra_detalle", args=[self.object.pk])


class ObraDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "facturacion.view_obra"
    model = Obra
    context_object_name = "obra"
    template_name = "facturacion/obras/detalle.html"


class ObraUpdateView(LoginRequiredMixin, PermissionRequiredMixin, AuditFormMixin, UpdateView):
    permission_required = "facturacion.change_obra"
    model = Obra
    form_class = ObraForm
    template_name = "facturacion/obras/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Obra actualizada.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("facturacion:obra_detalle", args=[self.object.pk])


class DocumentoTributarioListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "facturacion.view_documentotributario"
    model = DocumentoTributario
    context_object_name = "documentos"
    template_name = "facturacion/documentos/lista.html"
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related("cliente", "obra")
        cliente_id = self.kwargs.get("cliente_id")
        obra_id = self.kwargs.get("obra_id")
        if cliente_id:
            queryset = queryset.filter(cliente_id=cliente_id)
        if obra_id:
            queryset = queryset.filter(obra_id=obra_id)
        tipo = self.request.GET.get("tipo", "")
        estado = self.request.GET.get("estado", "")
        if tipo:
            queryset = queryset.filter(tipo_documento=tipo)
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tipos"] = DocumentoTributario.Tipo.choices
        context["estados"] = DocumentoTributario.Estado.choices
        context["tipo"] = self.request.GET.get("tipo", "")
        context["estado"] = self.request.GET.get("estado", "")
        return context


class DocumentoTributarioCreateView(LoginRequiredMixin, PermissionRequiredMixin, AuditFormMixin, CreateView):
    permission_required = "facturacion.add_documentotributario"
    model = DocumentoTributario
    form_class = DocumentoTributarioForm
    template_name = "facturacion/documentos/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.kwargs.get("cliente_id"):
            kwargs["cliente"] = get_object_or_404(Cliente, pk=self.kwargs["cliente_id"])
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Documento tributario registrado correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("facturacion:documento_detalle", args=[self.object.pk])


class DocumentoTributarioDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "facturacion.view_documentotributario"
    model = DocumentoTributario
    context_object_name = "documento"
    template_name = "facturacion/documentos/detalle.html"


class DocumentoTributarioUpdateView(LoginRequiredMixin, PermissionRequiredMixin, AuditFormMixin, UpdateView):
    permission_required = "facturacion.change_documentotributario"
    model = DocumentoTributario
    form_class = DocumentoTributarioForm
    template_name = "facturacion/documentos/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Documento tributario actualizado.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("facturacion:documento_detalle", args=[self.object.pk])


class DocumentoTributarioAnularView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "facturacion.change_documentotributario"

    def get(self, request, pk):
        documento = get_object_or_404(DocumentoTributario, pk=pk)
        return render(request, "facturacion/documentos/anular.html", {"documento": documento, "form": AnularDocumentoTributarioForm()})

    def post(self, request, pk):
        documento = get_object_or_404(DocumentoTributario, pk=pk)
        form = AnularDocumentoTributarioForm(request.POST)
        if form.is_valid():
            documento.estado = DocumentoTributario.Estado.ANULADA
            documento.actualizado_por = request.user
            documento.save(update_fields=["estado", "actualizado_por", "actualizado_en"])
            messages.success(request, "Documento tributario anulado.")
            return redirect("facturacion:documento_detalle", pk=documento.pk)
        return render(request, "facturacion/documentos/anular.html", {"documento": documento, "form": form})
