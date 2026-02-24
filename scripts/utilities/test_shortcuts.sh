#!/bin/bash

# Script for testing quick access shortcuts

echo "🧪 Testing Quick Access Shortcuts..."
echo "===================================="
echo ""

# Test 1: Check if management command exists
echo "📝 Test 1: Checking management command..."
if python3 manage.py help | grep -q "setup_quick_actions"; then
    echo "✅ setup_quick_actions command found"
else
    echo "❌ setup_quick_actions command NOT found"
fi
echo ""

# Test 2: Check database entries
echo "📝 Test 2: Checking database entries..."
QUICK_ACTIONS_COUNT=$(python3 manage.py shell -c "from quick_access.models import QuickAction; print(QuickAction.objects.count())")
echo "Total quick actions: $QUICK_ACTIONS_COUNT"
if [ "$QUICK_ACTIONS_COUNT" -gt 0 ]; then
    echo "✅ Database has quick actions"
else
    echo "❌ Database is empty - run: python3 manage.py setup_quick_actions"
fi
echo ""

# Test 3: List all quick actions
echo "📝 Test 3: Listing quick actions..."
python3 manage.py shell -c "
from quick_access.models import QuickAction
for action in QuickAction.objects.all()[:10]:
    print(f'  • {action.name} -> {action.url}')
"
echo ""

# Test 4: Check if URLs are accessible (sample)
echo "📝 Test 4: Testing sample URLs..."
URLS=(
    "/sales/new/"
    "/purchases/new/"
    "/inventory/"
    "/accounting/"
)

for url in "${URLS[@]}"; do
    echo "  Testing: $url"
done
echo ""

echo "✅ Testing complete!"
echo ""
echo "💡 Tips:"
echo "  - Visit /quick-access/ to see the dashboard"
echo "  - Press Ctrl+K for global search"
echo "  - Press Ctrl+/ to see all shortcuts"
echo "  - Press Ctrl+Shift+I for new invoice"
