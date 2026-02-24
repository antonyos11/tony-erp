#!/bin/bash
echo "=========================================="
echo "🧪 تشغيل جميع الاختبارات الرئيسية"
echo "=========================================="
echo ""

passed=0
failed=0
total=0

# الاختبارات الرئيسية العشرة
tests=(
    "TC001_verify_sales_invoice_creation_and_approval.py"
    "TC002_validate_inventory_product_listing_and_stock_management.py"
    "TC003_test_accounting_journal_entries_and_financial_reports.py"
    "TC004_crm_customer_management_and_opportunity_tracking.py"
    "TC005_production_order_management_and_quality_inspection.py"
    "TC006_pos_order_creation_and_thermal_printing.py"
    "TC007_hr_employee_attendance_and_payroll_processing.py"
    "TC008_fleet_vehicle_and_trip_management.py"
    "TC009_ecommerce_product_catalog_and_order_management.py"
    "TC010_whatsapp_ai_conversation_and_template_management.py"
)

for test in "${tests[@]}"; do
    total=$((total + 1))
    echo "[$total/10] اختبار: $test"
    
    if python3 "$test" > /dev/null 2>&1; then
        echo "   ✅ ناجح"
        passed=$((passed + 1))
    else
        echo "   ❌ فاشل"
        failed=$((failed + 1))
    fi
    echo ""
done

echo "=========================================="
echo "📊 النتائج النهائية"
echo "=========================================="
echo "✅ ناجح: $passed/$total"
echo "❌ فاشل: $failed/$total"
echo "📈 نسبة النجاح: $((passed * 100 / total))%"
echo "=========================================="
