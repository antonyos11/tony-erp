"""
Populate mattress raw-material categories with a full tree (Arabic labels).
Usage:
  python3 add_mattress_raw_material_categories.py
"""
import os
import sys
import django
from typing import Dict, List, Optional

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "accountant_pro.settings")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

# Ensure project root on path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

django.setup()

from inventory.models import Category  # noqa: E402

TreeNode = Dict[str, object]

def ensure_category(name: str, parent: Optional[Category], sort_order: int) -> Category:
    clean_name = name.strip()

    # إذا كانت الفئة موجودة باسم مطابق (حتى لو كان لها أب مختلف) نعيد استخدامها
    existing = Category.objects.filter(name=clean_name).first()
    if existing:
        return existing

    obj, _ = Category.objects.get_or_create(
        name=clean_name,
        parent=parent,
        defaults={"sort_order": sort_order, "is_active": True},
    )
    if obj.sort_order != sort_order:
        obj.sort_order = sort_order
        obj.save(update_fields=["sort_order"])
    return obj

def seed_tree(nodes: List[TreeNode], parent: Optional[Category] = None, depth: int = 0) -> int:
    """Recursively create Category nodes and return count created/updated."""
    count = 0
    for order, node in enumerate(nodes, start=1):
        name = str(node["name"]).strip()
        cat = ensure_category(name, parent, order)
        count += 1
        children = node.get("children") or []
        if children:
            count += seed_tree(children, cat, depth + 1)
    return count

def build_tree() -> List[TreeNode]:
    return [
        {
            "name": "الهيكل الداخلي للمرتبة",
            "children": [
                {
                    "name": "السوست (أنظمة النوابض)",
                    "children": [
                        {"name": "بونيل Bonnell"},
                        {"name": "بوكيت Pocket (فرادى / مربعات / زجزاج)"},
                        {"name": "سوست متصلة Continuous"},
                        {"name": "Offset"},
                        {"name": "Micro Springs"},
                        {"name": "إطار سوست محيط (Edge Support Spring)"},
                        {
                            "name": "إكسسوارات السوست",
                            "children": [
                                {"name": "سلك صلب عالي الكربون"},
                                {"name": "كليبسات تثبيت"},
                                {"name": "أسلاك ربط"},
                                {"name": "شريط قماش تثبيت السوست"},
                                {"name": "شبك حماية السوست"},
                                {"name": "كرتون سوست"},
                                {"name": "لباد سفلي علوي"},
                            ],
                        },
                    ],
                },
                {
                    "name": "طبقات العزل والفصل",
                    "children": [
                        {"name": "لباد حراري Thermo Felt (كثافات متعددة)"},
                        {"name": "لباد مضغوط"},
                        {"name": "سبون بوند Nonwoven"},
                        {"name": "فايبر عازل"},
                        {"name": "قماش بولي بروبلين"},
                        {"name": "كرتون صناعي مقوى"},
                    ],
                },
            ],
        },
        {
            "name": "طبقات الراحة (Comfort Layers)",
            "children": [
                {
                    "name": "الإسفنج",
                    "children": [
                        {"name": "PU Foam"},
                        {"name": "HR Foam"},
                        {"name": "Rebond Foam"},
                        {"name": "Memory Foam"},
                        {"name": "Gel Foam"},
                        {"name": "Latex طبيعي / صناعي"},
                        {"name": "Charcoal Foam"},
                        {"name": "Egg Crate Foam (مشرشر)"},
                    ],
                },
                {
                    "name": "حشوات التبطين",
                    "children": [
                        {"name": "فايبر بوليستر"},
                        {"name": "فايبر سيليكون"},
                        {"name": "قطن"},
                        {"name": "صوف صناعي"},
                        {"name": "Hollow Fiber"},
                    ],
                },
            ],
        },
        {
            "name": "الأقمشة الخارجية (Quilting & Cover)",
            "children": [
                {
                    "name": "أقمشة الوجه العلوي والسفلي",
                    "children": [
                        {"name": "قطن"},
                        {"name": "بولي قطن"},
                        {"name": "جاكار"},
                        {"name": "تريكو"},
                        {"name": "بامبو"},
                        {"name": "ساتان"},
                        {"name": "أقمشة تبريد Cooling Fabric"},
                        {"name": "أقمشة مضادة للبكتيريا"},
                    ],
                },
                {
                    "name": "طبقة الكويلت (التنجيد)",
                    "children": [
                        {"name": "إسفنج كويلت"},
                        {"name": "فايبر كويلت"},
                        {"name": "لباد خفيف"},
                        {"name": "خيط كويلت"},
                        {"name": "رسومات كويلت (مربعات – موجات – زخارف)"},
                    ],
                },
            ],
        },
        {
            "name": "الإكسسوارات الخارجية للمرتبة",
            "children": [
                {
                    "name": "اليدات (Handles)",
                    "children": [
                        {"name": "يد قماش عادية"},
                        {"name": "يد مبطنة"},
                        {"name": "يد جلد صناعي"},
                        {"name": "يد جلد طبيعي"},
                        {"name": "يد بلاستيك صناعي"},
                        {"name": "يد مطاط"},
                        {"name": "يد مطبوعة باللوجو"},
                        {
                            "name": "مكونات اليد",
                            "children": [
                                {"name": "شريط نايلون داخلي"},
                                {"name": "حشو فايبر"},
                                {"name": "خيط تثبيت قوي"},
                                {"name": "بطانة جلد / قماش"},
                            ],
                        },
                    ],
                },
                {
                    "name": "شريط الجنب (Border Tape / Ticking)",
                    "children": [
                        {"name": "شريط قماش عادي"},
                        {"name": "شريط جاكار"},
                        {"name": "شريط مطبوع"},
                        {"name": "شريط مطرز"},
                        {"name": "شريط مبطن"},
                        {"name": "شريط مزخرف فخم"},
                        {
                            "name": "عرض الشريط",
                            "children": [
                                {"name": "18 سم"},
                                {"name": "22 سم"},
                                {"name": "25 سم"},
                                {"name": "30 سم"},
                            ],
                        },
                    ],
                },
                {
                    "name": "شريط التزيين (Decorative Tape)",
                    "children": [
                        {"name": "شريط ساتان"},
                        {"name": "شريط جاكار"},
                        {"name": "شريط حرير صناعي"},
                        {"name": "شريط PVC"},
                        {"name": "شريط تطريز"},
                        {"name": "شريط ذهبي / فضي"},
                        {"name": "شريط لوجو مطبوع"},
                    ],
                },
                {
                    "name": "الشريط ثلاثي الأبعاد (3D Tape / 3D Border)",
                    "children": [
                        {"name": "شريط 3D قماش"},
                        {"name": "شريط 3D شبكي (تهوية)"},
                        {"name": "شريط 3D إسفنج"},
                        {"name": "شريط تهوية جانبي Air Mesh"},
                        {
                            "name": "استخدام الشريط",
                            "children": [
                                {"name": "تهوية المرتبة"},
                                {"name": "شكل فخم"},
                                {"name": "تقليل الرطوبة"},
                                {"name": "دعم الحواف"},
                            ],
                        },
                    ],
                },
                {
                    "name": "فتحات التهوية (Ventilation Accessories)",
                    "children": [
                        {"name": "فتحات تهوية معدنية"},
                        {"name": "فتحات بلاستيك"},
                        {"name": "فتحات مطاط"},
                        {"name": "فتحات مدمجة في شريط 3D"},
                    ],
                },
            ],
        },
        {
            "name": "الإكسسوارات الوظيفية",
            "children": [
                {"name": "زراير كبس"},
                {"name": "أزرار قماش"},
                {"name": "كباسين"},
                {"name": "سوست (Zip)"},
                {"name": "فيلكرو"},
                {"name": "شريط مطاط"},
                {"name": "شريط مانع انزلاق"},
                {"name": "مقابض تثبيت جانبية"},
            ],
        },
        {
            "name": "المواد اللاصقة والتثبيت",
            "children": [
                {"name": "غراء مائي"},
                {"name": "غراء حراري"},
                {"name": "غراء رش"},
                {"name": "خيوط بوليستر صناعي"},
                {"name": "خيوط نايلون"},
                {"name": "دبابيس معدنية"},
                {"name": "خيوط تقوية"},
            ],
        },
        {
            "name": "الملصقات والعلامات",
            "children": [
                {"name": "ليبل قماش"},
                {"name": "ليبل جلد"},
                {"name": "ليبل مطبوع"},
                {"name": "ليبل غسيل"},
                {"name": "ليبل تعليمات الاستخدام"},
                {"name": "هولوجرام أصلي"},
                {"name": "باركود"},
            ],
        },
        {
            "name": "التشطيب والتغليف",
            "children": [
                {"name": "أكياس بلاستيك"},
                {"name": "أكياس فاكيوم"},
                {"name": "رول نايلون"},
                {"name": "كرتون"},
                {"name": "شريط لاصق"},
                {"name": "استيكرات"},
                {"name": "أكياس سيليكا"},
            ],
        },
        {
            "name": "إكسسوارات المخدات واللحاف (للتكامل)",
            "children": [
                {"name": "سوست مخدة"},
                {"name": "أزرار مخدة"},
                {"name": "شريط لحاف"},
                {"name": "كباسين لحاف"},
                {"name": "شريط تزيين لحاف"},
            ],
        },
    ]

def main():
    tree = build_tree()
    total = seed_tree(tree)
    print(f"✅ تم إنشاء/تحديث {total} فئة مواد خام")

if __name__ == "__main__":
    main()
