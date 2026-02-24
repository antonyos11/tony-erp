#!/bin/bash
echo "📊 تحليل نتائج الاختبارات النهائية"
echo "=================================="
echo ""
total=$(grep -c "========== TC" final_test_run.log)
passed=$(grep -c "✅ PASSED" final_test_run.log)
failed=$(grep -c "❌ FAILED" final_test_run.log)

echo "إجمالي الاختبارات: $total"
echo "ناجح ✅: $passed"
echo "فاشل ❌: $failed"
echo ""
echo "نسبة النجاح: $(echo "scale=1; $passed * 100 / $total" | bc)%"
echo ""
echo "الاختبارات الناجحة:"
echo "===================="
grep -B1 "✅ PASSED" final_test_run.log | grep "========" | sed 's/==========//g' | sed 's/^[ \t]*//' | head -20
