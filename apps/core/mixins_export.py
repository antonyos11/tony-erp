"""
Export Mixin — يُضاف لأي ListView لإضافة زر تصدير Excel/PDF
RITA ERP Sprint 25
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.export import export_to_excel, export_queryset_to_pdf


class ExportMixin:
    """
    Mixin يضيف وظيفة التصدير إلى أي ListView.
    
    كيفية الاستخدام:
    ─────────────────
    class MyListView(ExportMixin, LoginRequiredMixin, ListView):
        export_filename = 'my_data'
        export_title    = 'بياناتي'
        export_columns  = [
            {'header': 'الكود', 'field': 'code', 'width': 15},
            {'header': 'الاسم', 'field': 'name', 'width': 30},
        ]
    
    في الـ template:
    ─────────────────
    <a href="?export=excel" class="btn btn-success">
        <i class="fas fa-file-excel"></i> Excel
    </a>
    <a href="?export=pdf" class="btn btn-danger">
        <i class="fas fa-file-pdf"></i> PDF
    </a>
    """

    export_filename: str = 'export'
    export_title: str = 'تصدير البيانات'
    export_columns: list = []
    export_sheet_name: str = 'البيانات'

    def get_export_queryset(self):
        """يمكن تجاوزه لتعديل الاستعلام عند التصدير (بدون pagination)"""
        return self.get_queryset()

    def get_export_columns(self) -> list:
        """يمكن تجاوزه لتعديل الأعمدة ديناميكيًا"""
        return self.export_columns

    def get(self, request, *args, **kwargs):
        export_format = request.GET.get('export')

        if export_format == 'excel':
            qs = self.get_export_queryset()
            cols = self.get_export_columns()
            if not cols:
                from django.http import HttpResponseBadRequest
                return HttpResponseBadRequest('export_columns غير معرّف')
            return export_to_excel(
                queryset=qs,
                columns=cols,
                filename=self.export_filename,
                sheet_name=self.export_sheet_name,
            )

        if export_format == 'pdf':
            qs = self.get_export_queryset()
            cols = self.get_export_columns()
            if not cols:
                from django.http import HttpResponseBadRequest
                return HttpResponseBadRequest('export_columns غير معرّف')
            return export_queryset_to_pdf(
                queryset=qs,
                columns=cols,
                title=self.export_title,
                filename=self.export_filename,
            )

        return super().get(request, *args, **kwargs)
