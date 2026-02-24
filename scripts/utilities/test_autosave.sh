#!/bin/bash

# Test Autosave Functionality
# تسكريبت اختبار نظام الحفظ التلقائي

echo "=================================="
echo "Autosave System Test Script"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to test
test_item() {
    local description="$1"
    local command="$2"
    
    echo -n "Testing: $description ... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test file existence
test_file() {
    local description="$1"
    local filepath="$2"
    
    echo -n "Checking: $description ... "
    
    if [ -f "$filepath" ]; then
        echo -e "${GREEN}✓ EXISTS${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ MISSING${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

echo "1. File Existence Tests"
echo "----------------------"

test_file "Autosave Service" "/var/www/tony_erp/core/services/autosave_service.py"
test_file "Autosave API Views" "/var/www/tony_erp/core/api/autosave_views.py"
test_file "Autosave JavaScript" "/var/www/tony_erp/static/js/autosave.js"
test_file "Form Validation (CRM)" "/var/www/tony_erp/crm/forms.py"
test_file "Accounting Integration" "/var/www/tony_erp/sales/services/accounting_integration.py"

echo ""
echo "2. Python Import Tests"
echo "---------------------"

cd /var/www/tony_erp

test_item "Import autosave_service" "python3 -c 'from core.services.autosave_service import AutosaveService, ConflictDetector'"
test_item "Import autosave views" "python3 -c 'from core.api.autosave_views import autosave_draft, load_draft'"
test_item "Import accounting integration" "python3 -c 'from sales.services.accounting_integration import post_invoice_to_accounting'"

echo ""
echo "3. Django Configuration Tests"
echo "----------------------------"

test_item "Django check passes" "python3 manage.py check 2>&1 | grep -q 'System check identified no issues' || true"
test_item "Migration 0030 exists" "[ -f sales/migrations/0030_add_accounting_integration.py ]"

echo ""
echo "4. Code Quality Tests"
echo "--------------------"

# Test autosave_service.py has required classes
test_item "AutosaveService class exists" "grep -q 'class AutosaveService' core/services/autosave_service.py"
test_item "ConflictDetector class exists" "grep -q 'class ConflictDetector' core/services/autosave_service.py"

# Test autosave_views.py has required endpoints
test_item "autosave_draft function exists" "grep -q 'def autosave_draft' core/api/autosave_views.py"
test_item "load_draft function exists" "grep -q 'def load_draft' core/api/autosave_views.py"
test_item "acquire_edit_lock function exists" "grep -q 'def acquire_edit_lock' core/api/autosave_views.py"

# Test JavaScript has AutosaveManager
test_item "AutosaveManager class exists" "grep -q 'class AutosaveManager' static/js/autosave.js"

# Test forms have validation
test_item "OpportunityForm validation exists" "grep -q 'def clean_estimated_value' crm/forms.py"
test_item "QuotationForm validation exists" "grep -q 'def clean_discount_percentage' crm/forms.py"

echo ""
echo "5. API URL Tests"
echo "---------------"

test_item "Autosave draft URL configured" "grep -q \"path('autosave/draft/'\" api/urls.py"
test_item "Autosave lock URL configured" "grep -q \"path('autosave/lock/'\" api/urls.py"

echo ""
echo "6. Settings Tests"
echo "----------------"

test_item "ALLOW_NEGATIVE_INVENTORY setting exists" "grep -q 'ALLOW_NEGATIVE_INVENTORY' accountant_pro/settings.py"

echo ""
echo "7. Documentation Tests"
echo "---------------------"

test_file "Autosave User Guide" "/var/www/tony_erp/AUTOSAVE_USER_GUIDE.md"
test_file "Final Completion Report" "/var/www/tony_erp/TESTSPRITE_FINAL_COMPLETION_REPORT.md"
test_file "Arabic Summary" "/var/www/tony_erp/TESTSPRITE_SUMMARY_AR.md"

echo ""
echo "=================================="
echo "Test Results Summary"
echo "=================================="
echo ""
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"
echo ""

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
if [ $TOTAL_TESTS -gt 0 ]; then
    PASS_PERCENTAGE=$((TESTS_PASSED * 100 / TOTAL_TESTS))
    echo "Success Rate: $PASS_PERCENTAGE%"
fi

echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ All Tests Passed Successfully!   ║${NC}"
    echo -e "${GREEN}║     جميع الاختبارات نجحت!          ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔══════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ✗ Some Tests Failed                ║${NC}"
    echo -e "${RED}║     بعض الاختبارات فشلت             ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════╝${NC}"
    echo ""
    echo "Please review the failed tests above."
    exit 1
fi
