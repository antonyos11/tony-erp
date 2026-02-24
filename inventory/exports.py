"""
Advanced export functionality for inventory management
"""

import io
import os
import json
from datetime import datetime
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class InventoryExporter:
    """Advanced exporter for inventory data"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._arabic_font_name = None  # cache once registered

    # ==============================
    # Arabic PDF helpers
    # ==============================
    def _find_arabic_font_path(self):
        """Try to locate a TTF font that supports Arabic. Priority:
        1) settings.ARABIC_TTF_PATH if provided
        2) Common Windows fonts (Arial, Tahoma)
        3) Common Linux Noto fonts
        4) Common macOS fonts (GeezaPro)
        Returns a file path string or None.
        """
        # From settings
        try:
            ttf_path = getattr(settings, 'ARABIC_TTF_PATH', None)
            if ttf_path and os.path.exists(ttf_path):
                return ttf_path
        except Exception:
            pass
        # Windows
        candidates = [
            r"C:\\Windows\\Fonts\\arial.ttf",
            r"C:\\Windows\\Fonts\\Tahoma.ttf",
            r"C:\\Windows\\Fonts\\segoeui.ttf",
        ]
        # Linux
        candidates += [
            "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoKufiArabic-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        # macOS
        candidates += [
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/ Geeza Pro.ttf",
            "/System/Library/Fonts/Geeza Pro.ttf",
        ]
        for p in candidates:
            try:
                if os.path.exists(p):
                    return p
            except Exception:
                continue
        return None

    def _register_arabic_font(self):
        """Register an Arabic-capable TTF with ReportLab and cache the font name."""
        if self._arabic_font_name:
            return self._arabic_font_name
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
        except Exception:
            return None
        path = self._find_arabic_font_path()
        if not path:
            return None
        try:
            font_name = 'Arabic'
            # If already registered, skip
            try:
                pdfmetrics.getFont(font_name)
                self._arabic_font_name = font_name
                return font_name
            except Exception:
                pass
            pdfmetrics.registerFont(TTFont(font_name, path))
            self._arabic_font_name = font_name
            return font_name
        except Exception:
            return None

    def _shape_ar(self, text):
        """Arabic shaping + bidi reordering for ReportLab rendering."""
        if text is None:
            return ''
        try:
            import importlib
            reshaper = importlib.import_module('arabic_reshaper')
            bidi = importlib.import_module('bidi.algorithm')
            # Ensure input is str
            s = str(text)
            reshaped = reshaper.reshape(s)
            return bidi.get_display(reshaped)
        except Exception:
            # If shaping not available, return as-is
            return str(text)
    
    def export_products_excel(self, products, filename="products"):
        """Export products to Excel format"""
        try:
            # Dynamic import to avoid static analysis errors when package is missing
            import importlib
            pd = importlib.import_module("pandas")
            
            # Prepare data
            data = []
            for product in products:
                data.append({
                    'اسم المنتج': product.name,
                    'رمز المنتج': product.sku,
                    'الوصف': product.description or '',
                    'الباركود': product.barcode or '',
                    'السعر': float(product.price),
                    'التكلفة': float(product.cost),
                    'المخزون الحالي': product.current_stock,
                    'الحد الأدنى': product.min_stock,
                    'القيمة الإجمالية': float(product.total_value),
                    'وحدة الشراء': product.get_purchase_uom_display(),
                    'وحدة الاستخدام': product.get_usage_uom_display(),
                    'نشط': 'نعم' if product.is_active else 'لا',
                    'مخزون منخفض': 'نعم' if product.is_low_stock else 'لا',
                })
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Write to an in-memory buffer, then return a response
            buffer = io.BytesIO()
            
            # Write to Excel (requires openpyxl engine)
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='المنتجات', index=False)
                
                # Add summary sheet
                summary_data = {
                    'إحصائية': [
                        'إجمالي المنتجات',
                        'المنتجات النشطة',
                        'المنتجات غير النشطة',
                        'منتجات مخزون منخفض',
                        'منتجات نفد مخزونها',
                        'إجمالي قيمة المخزون',
                    ],
                    'القيمة': [
                        len(products),
                        len([p for p in products if p.is_active]),
                        len([p for p in products if not p.is_active]),
                        len([p for p in products if p.is_low_stock]),
                        len([p for p in products if p.current_stock == 0]),
                        sum(float(p.total_value) for p in products),
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='الملخص', index=False)
            buffer.seek(0)
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="{filename}_{self.timestamp}.xlsx"'
            response.write(buffer.getvalue())
            return response
            
        except ImportError:
            # Fallback to CSV if pandas not available
            return self.export_products_csv(products, filename)
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            return self.export_products_csv(products, filename)
    
    def export_products_csv(self, products, filename="products"):
        """Export products to CSV format"""
        import csv
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}_{self.timestamp}.csv"'
        
        # Add BOM for proper UTF-8 encoding in Excel
        response.write('\ufeff')
        
        writer = csv.writer(response)
        
        # Headers
        writer.writerow([
            'اسم المنتج', 'رمز المنتج', 'الوصف', 'الباركود', 'السعر', 'التكلفة',
            'المخزون الحالي', 'الحد الأدنى', 'القيمة الإجمالية', 'وحدة الشراء',
            'وحدة الاستخدام', 'نشط', 'مخزون منخفض'
        ])
        
        # Data
        for product in products:
            writer.writerow([
                product.name,
                product.sku,
                product.description or '',
                product.barcode or '',
                float(product.price),
                float(product.cost),
                product.current_stock,
                product.min_stock,
                float(product.total_value),
                product.get_purchase_uom_display(),
                product.get_usage_uom_display(),
                'نعم' if product.is_active else 'لا',
                'نعم' if product.is_low_stock else 'لا',
            ])
        
        return response
    
    def export_products_pdf(self, products, filename="products"):
        """Export products to PDF format"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            # Build PDF into a buffer, then write to response
            pdf_buffer = io.BytesIO()
            
            # Create PDF document
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
            elements = []
            
            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=1,  # Center
            )
            # Register and apply Arabic font if available
            font_name = self._register_arabic_font()
            if font_name:
                title_style.fontName = font_name
            
            # Title
            title = Paragraph(self._shape_ar(f"تقرير المنتجات - {datetime.now().strftime('%Y-%m-%d')}"), title_style)
            elements.append(title)
            
            # Table data
            data = [[
                self._shape_ar('اسم المنتج'),
                self._shape_ar('رمز المنتج'),
                self._shape_ar('المخزون'),
                self._shape_ar('السعر'),
                self._shape_ar('التكلفة'),
                self._shape_ar('القيمة الإجمالية')
            ]]
            
            for product in products[:50]:  # Limit for PDF
                data.append([
                    self._shape_ar(product.name[:20] + '...' if len(product.name) > 20 else product.name),
                    self._shape_ar(product.sku),
                    self._shape_ar(str(product.current_stock)),
                    self._shape_ar(f"{float(product.price):.2f}"),
                    self._shape_ar(f"{float(product.cost):.2f}"),
                    self._shape_ar(f"{float(product.total_value):.2f}"),
                ])
            
            # Create table
            table = Table(data, colWidths=[2*inch, 1*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), font_name or 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            if font_name:
                table.setStyle(TableStyle([
                    ('FONTNAME', (0, 1), (-1, -1), font_name),
                ]))
            
            elements.append(table)
            
            # Build PDF
            doc.build(elements)
            pdf_buffer.seek(0)
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}_{self.timestamp}.pdf"'
            response.write(pdf_buffer.getvalue())
            return response
            
        except ImportError:
            logger.warning("ReportLab not available, falling back to HTML")
            return self.export_products_html(products, filename)
        except Exception as e:
            logger.error(f"Error exporting to PDF: {e}")
            return self.export_products_html(products, filename)
    
    def export_products_html(self, products, filename="products"):
        """Export products to HTML format (fallback)"""
        html_content = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <title>تقرير المنتجات</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
                th {{ background-color: #f2f2f2; }}
                .header {{ text-align: center; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>تقرير المنتجات</h1>
                <p>تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>اسم المنتج</th>
                        <th>رمز المنتج</th>
                        <th>المخزون الحالي</th>
                        <th>الحد الأدنى</th>
                        <th>السعر</th>
                        <th>التكلفة</th>
                        <th>القيمة الإجمالية</th>
                        <th>الحالة</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for product in products:
            status = "نفد المخزون" if product.current_stock == 0 else "مخزون منخفض" if product.is_low_stock else "متوفر"
            html_content += f"""
                    <tr>
                        <td>{product.name}</td>
                        <td>{product.sku}</td>
                        <td>{product.current_stock}</td>
                        <td>{product.min_stock}</td>
                        <td>{float(product.price):.2f}</td>
                        <td>{float(product.cost):.2f}</td>
                        <td>{float(product.total_value):.2f}</td>
                        <td>{status}</td>
                    </tr>
            """
        
        html_content += """
                </tbody>
            </table>
        </body>
        </html>
        """
        
        response = HttpResponse(html_content, content_type='text/html; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}_{self.timestamp}.html"'
        return response
    
    def export_locations_excel(self, locations, filename="locations"):
        """Export locations to Excel format"""
        try:
            # Dynamic import to avoid static analysis errors when package is missing
            import importlib
            pd = importlib.import_module("pandas")
            
            data = []
            for location in locations:
                stock_count = location.stocks.count()
                total_value = sum(stock.total_value for stock in location.stocks.all())
                
                data.append({
                    'اسم الموقع': location.name,
                    'رمز الموقع': location.code,
                    'النوع': location.get_type_display(),
                    'العنوان': location.address or '',
                    'عدد المنتجات': stock_count,
                    'القيمة الإجمالية': float(total_value),
                    'نشط': 'نعم' if location.is_active else 'لا',
                    'افتراضي': 'نعم' if location.is_default else 'لا',
                })
            
            df = pd.DataFrame(data)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='المواقع', index=False)
            buffer.seek(0)
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="{filename}_{self.timestamp}.xlsx"'
            response.write(buffer.getvalue())
            return response
            
        except ImportError:
            return self.export_locations_csv(locations, filename)
        except Exception as e:
            logger.error(f"Error exporting locations to Excel: {e}")
            return self.export_locations_csv(locations, filename)
    
    def export_locations_csv(self, locations, filename="locations"):
        """Export locations to CSV format"""
        import csv
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}_{self.timestamp}.csv"'
        response.write('\ufeff')  # BOM for UTF-8
        
        writer = csv.writer(response)
        writer.writerow(['اسم الموقع', 'رمز الموقع', 'النوع', 'العنوان', 'عدد المنتجات', 'القيمة الإجمالية', 'نشط', 'افتراضي'])
        
        for location in locations:
            stock_count = location.stocks.count()
            total_value = sum(stock.total_value for stock in location.stocks.all())
            
            writer.writerow([
                location.name,
                location.code,
                location.get_type_display(),
                location.address or '',
                stock_count,
                float(total_value),
                'نعم' if location.is_active else 'لا',
                'نعم' if location.is_default else 'لا',
            ])
        
        return response
    
    def generate_stock_chart(self, products):
        """Generate stock analysis chart"""
        try:
            # Dynamic import via importlib to reduce static resolution errors
            import importlib
            matplotlib = importlib.import_module('matplotlib')
            matplotlib.use('Agg')  # Use non-interactive backend
            plt = importlib.import_module('matplotlib.pyplot')
            from io import BytesIO
            import base64
            
            # Prepare data
            product_names = [p.name[:15] + '...' if len(p.name) > 15 else p.name for p in products[:10]]
            stock_quantities = [p.current_stock for p in products[:10]]
            stock_values = [float(p.total_value) for p in products[:10]]
            
            if not product_names:
                return None
            
            # Create figure with subplots
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # Chart 1: Stock Quantities
            bars1 = ax1.bar(product_names, stock_quantities, color=['red' if q == 0 else 'orange' if q < 10 else 'green' for q in stock_quantities])
            ax1.set_title('كميات المخزون', fontsize=14, fontweight='bold')
            ax1.set_ylabel('الكمية')
            ax1.tick_params(axis='x', rotation=45)
            
            # Add value labels on bars
            for bar, qty in zip(bars1, stock_quantities):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + 0.5, str(qty),
                        ha='center', va='bottom', fontweight='bold')
            
            # Chart 2: Stock Values (Pie Chart)
            if sum(stock_values) > 0:
                ax2.pie(stock_values, labels=product_names, autopct='%1.1f%%', startangle=90)
                ax2.set_title('توزيع قيم المخزون', fontsize=14, fontweight='bold')
            else:
                ax2.text(0.5, 0.5, 'لا توجد قيم للعرض', ha='center', va='center', transform=ax2.transAxes)
                ax2.set_title('توزيع قيم المخزون', fontsize=14, fontweight='bold')
            
            # Adjust layout
            plt.tight_layout()
            
            # Save to string
            buffer = BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            plt.close()
            
            # Encode to base64
            graphic = base64.b64encode(image_png).decode('utf-8')
            
            return f'<img src="data:image/png;base64,{graphic}" class="img-fluid" alt="Stock Chart">'
            
        except ImportError:
            logger.warning("Matplotlib not available")
            return None
        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            return None

    # ==============================
    # Requisitions export helpers
    # ==============================
    def _requisition_rows(self, requisitions):
        rows = []
        for r in requisitions:
            items = list(getattr(r, 'items').all()) if hasattr(r, 'items') else []
            rows.append({
                'number': r.number,
                'date': getattr(r, 'request_date', ''),
                'dept': r.from_department,
                'reference': r.reference or '',
                'status': r.get_status_display() if hasattr(r, 'get_status_display') else getattr(r, 'status', ''),
                'items_count': len(items),
                'qty_total': sum(int(getattr(i, 'quantity', 0) or 0) for i in items),
            })
        return rows

    def export_requisitions_excel(self, requisitions, filename="requisitions"):
        try:
            import importlib
            pd = importlib.import_module("pandas")
            rows = self._requisition_rows(requisitions)
            df = pd.DataFrame([{
                'رقم الطلب': r['number'],
                'التاريخ': r['date'],
                'القسم الطالب': r['dept'],
                'المرجع': r['reference'],
                'الحالة': r['status'],
                'عدد البنود': r['items_count'],
                'إجمالي الكمية': r['qty_total'],
            } for r in rows])
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='طلبات الخامات', index=False)
            buffer.seek(0)
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="{filename}_{self.timestamp}.xlsx"'
            response.write(buffer.getvalue())
            return response
        except Exception as e:
            logger.error(f"export_requisitions_excel error: {e}")
            return self.export_requisitions_csv(requisitions, filename)

    def export_requisitions_csv(self, requisitions, filename="requisitions"):
        import csv
        rows = self._requisition_rows(requisitions)
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}_{self.timestamp}.csv"'
        response.write('\ufeff')
        w = csv.writer(response)
        w.writerow(['رقم الطلب','التاريخ','القسم الطالب','المرجع','الحالة','عدد البنود','إجمالي الكمية'])
        for r in rows:
            w.writerow([r['number'], r['date'], r['dept'], r['reference'], r['status'], r['items_count'], r['qty_total']])
        return response

    def export_requisitions_pdf(self, requisitions, filename="requisitions"):
        try:
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []
            font_name = self._register_arabic_font()
            title_style = styles['Title']
            if font_name:
                title_style.fontName = font_name
            elements.append(Paragraph(self._shape_ar('تقرير طلبات الخامات'), title_style))
            data = [['رقم الطلب','التاريخ','القسم','المرجع','الحالة','عدد البنود','إجمالي الكمية']]
            # Shape header
            data = [[
                self._shape_ar('رقم الطلب'),
                self._shape_ar('التاريخ'),
                self._shape_ar('القسم'),
                self._shape_ar('المرجع'),
                self._shape_ar('الحالة'),
                self._shape_ar('عدد البنود'),
                self._shape_ar('إجمالي الكمية'),
            ]]
            for r in self._requisition_rows(requisitions)[:200]:
                data.append([
                    self._shape_ar(r['number']),
                    self._shape_ar(str(r['date'])),
                    self._shape_ar(r['dept']),
                    self._shape_ar(r['reference']),
                    self._shape_ar(r['status']),
                    self._shape_ar(r['items_count']),
                    self._shape_ar(r['qty_total']),
                ])
            tbl = Table(data, colWidths=[1.2*inch, 1*inch, 1.2*inch, 1.2*inch, 1*inch, 1*inch, 1*inch])
            tbl.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0), colors.grey),
                ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke),
                ('GRID',(0,0),(-1,-1), 0.5, colors.black),
                ('FONTSIZE',(0,0),(-1,-1), 8),
            ]))
            if font_name:
                tbl.setStyle(TableStyle([
                    ('FONTNAME',(0,0),(-1,-1), font_name),
                ]))
            elements.append(tbl)
            doc.build(elements)
            pdf_buffer.seek(0)
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}_{self.timestamp}.pdf"'
            response.write(pdf_buffer.getvalue())
            return response
        except Exception as e:
            logger.error(f"export_requisitions_pdf error: {e}")
            # fallback to HTML
            html = self._requisitions_fallback_html(requisitions)
            resp = HttpResponse(html, content_type='text/html; charset=utf-8')
            resp['Content-Disposition'] = f'attachment; filename="{filename}_{self.timestamp}.html"'
            return resp

    def _requisitions_fallback_html(self, requisitions):
        rows = self._requisition_rows(requisitions)
        html = [
            '<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8"><title>طلبات الخامات</title>',
            '<style>table{width:100%;border-collapse:collapse}th,td{border:1px solid #ddd;padding:6px;text-align:center}th{background:#f2f2f2}</style></head><body>',
            '<h2>تقرير طلبات الخامات</h2>',
            '<table><thead><tr><th>رقم</th><th>التاريخ</th><th>القسم</th><th>مرجع</th><th>الحالة</th><th>عدد البنود</th><th>إجمالي الكمية</th></tr></thead><tbody>'
        ]
        for r in rows:
            html.append(f"<tr><td>{r['number']}</td><td>{r['date']}</td><td>{r['dept']}</td><td>{r['reference']}</td><td>{r['status']}</td><td>{r['items_count']}</td><td>{r['qty_total']}</td></tr>")
        html.append('</tbody></table></body></html>')
        return ''.join(html)