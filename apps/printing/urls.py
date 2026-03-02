"""
URLs تطبيق الطباعة والباركود — RITA ERP
"""
from django.urls import path
from apps.printing import views

app_name = 'printing'

urlpatterns = [
    # الفواتير والإيصالات
    path('invoice/<int:pk>/',        views.PrintInvoiceView.as_view(),      name='print_invoice'),
    path('receipt/<int:pk>/',        views.PrintReceiptView.as_view(),       name='print_receipt'),

    # الباركود
    path('barcode/',                 views.GenerateBarcodeView.as_view(),    name='generate_barcode'),
    path('barcode/product/<int:product_pk>/', views.GenerateBarcodeView.as_view(), name='product_barcode'),
    path('barcode/sheet/',           views.PrintBarcodeSheetView.as_view(),  name='barcode_sheet'),

    # قوالب الطباعة
    path('templates/',               views.PrintTemplateListView.as_view(),    name='template_list'),

    # ملصقات المنتجات
    path('labels/',                  views.PrintProductLabelsView.as_view(),   name='product_labels'),
    path('labels/select/',           views.PrintProductLabelsSelectorView.as_view(), name='label_selector'),
]
