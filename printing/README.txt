Printing app: unified outputs for warranty labels.
Endpoints:
- /printing/warranty/<unit_id>/json/
- /printing/warranty/<unit_id>/zpl/
- /printing/warranty/<unit_id>/escpos/

Uses FinishedGoodUnit with fields: product, unit_serial, barcode, warranty_policy, qr_code_data.
