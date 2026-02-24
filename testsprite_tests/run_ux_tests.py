#!/usr/bin/env python3
"""
🎨 اختبار UX شامل لنظام Tony ERP باستخدام Playwright + TestSprite
"""
import asyncio
import time
from playwright.async_api import async_playwright


BASE_URL = "http://72.62.176.249"
USERNAME = "boss"
PASSWORD = "Mm02022006"


class UXTestSuite:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0

    def record(self, name, status, detail=""):
        self.results.append({"name": name, "status": status, "detail": detail})
        if status == "PASS":
            self.passed += 1
        else:
            self.failed += 1
        icon = "✅" if status == "PASS" else "❌"
        print(f"  {icon} {name} — {detail}")

    async def run(self):
        print("=" * 60)
        print("🎨 Tony ERP — UX Testing Suite (TestSprite + Playwright)")
        print("=" * 60)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="ar",
            )
            page = await context.new_page()

            # ─── 1. تسجيل الدخول ───
            print("\n📌 [1/10] تسجيل الدخول")
            await self.test_login(page)

            # ─── 2. تحميل Dashboard ───
            print("\n📌 [2/10] لوحة التحكم (Dashboard)")
            await self.test_dashboard(page)

            # ─── 3. التنقل بين الصفحات ───
            print("\n📌 [3/10] التنقل (Navigation)")
            await self.test_navigation(page)

            # ─── 4. RTL & Arabic ───
            print("\n📌 [4/10] دعم العربية و RTL")
            await self.test_rtl(page)

            # ─── 5. Responsive ───
            print("\n📌 [5/10] التصميم المتجاوب (Responsive)")
            await self.test_responsive(page, context)

            # ─── 6. النماذج (Forms) ───
            print("\n📌 [6/10] التحقق من النماذج (Forms Validation)")
            await self.test_forms(page)

            # ─── 7. البحث ───
            print("\n📌 [7/10] البحث الشامل")
            await self.test_search(page)

            # ─── 8. الأداء ───
            print("\n📌 [8/10] أداء تحميل الصفحات")
            await self.test_performance(page)

            # ─── 9. رسائل الخطأ ───
            print("\n📌 [9/10] رسائل الخطأ والنجاح")
            await self.test_error_messages(page)

            # ─── 10. إمكانية الوصول (Accessibility) ───
            print("\n📌 [10/10] إمكانية الوصول (Accessibility)")
            await self.test_accessibility(page)

            await browser.close()

        self.print_summary()

    # ──────────────────────────────────────
    async def test_login(self, page):
        try:
            await page.goto(f"{BASE_URL}/login/", timeout=15000)
            await page.wait_for_load_state("networkidle")

            title = await page.title()
            self.record("صفحة تسجيل الدخول", "PASS", f"Title: {title}")

            user_input = page.locator('input[name="username"], input[type="text"]').first
            pass_input = page.locator('input[name="password"], input[type="password"]').first
            await user_input.fill(USERNAME)
            await pass_input.fill(PASSWORD)

            btn = page.locator('button[type="submit"], input[type="submit"]').first
            await btn.click()
            await page.wait_for_load_state("networkidle", timeout=10000)

            if "/login" not in page.url:
                self.record("تسجيل الدخول بنجاح", "PASS", f"Redirected to {page.url}")
            else:
                self.record("تسجيل الدخول بنجاح", "FAIL", "لم يتم التوجيه")
        except Exception as e:
            self.record("تسجيل الدخول", "FAIL", str(e)[:100])

    async def test_dashboard(self, page):
        try:
            await page.goto(f"{BASE_URL}/dashboard/", timeout=15000)
            await page.wait_for_load_state("networkidle")

            content = await page.content()
            has_content = len(content) > 500
            self.record("تحميل لوحة التحكم", "PASS" if has_content else "FAIL",
                        f"Content size: {len(content)} chars")

            sidebar = page.locator('.sidebar, #sidebar, [class*="sidebar"], nav')
            count = await sidebar.count()
            self.record("وجود القائمة الجانبية (Sidebar)", "PASS" if count > 0 else "FAIL",
                        f"Found {count} sidebar elements")

            navbar = page.locator('.navbar, #navbar, [class*="navbar"], header')
            count = await navbar.count()
            self.record("وجود شريط التنقل (Navbar)", "PASS" if count > 0 else "FAIL",
                        f"Found {count} navbar elements")

        except Exception as e:
            self.record("لوحة التحكم", "FAIL", str(e)[:100])

    async def test_navigation(self, page):
        pages_to_test = [
            ("/dashboard/", "لوحة التحكم"),
            ("/products/", "المنتجات"),
            ("/customers/", "العملاء"),
            ("/sales/invoices/", "فواتير المبيعات"),
            ("/accounting/", "المحاسبة"),
        ]
        for path, name in pages_to_test:
            try:
                resp = await page.goto(f"{BASE_URL}{path}", timeout=10000)
                status = resp.status if resp else 0
                ok = status in (200, 301, 302)
                self.record(f"التنقل → {name}", "PASS" if ok else "FAIL",
                            f"Status {status}")
            except Exception as e:
                self.record(f"التنقل → {name}", "FAIL", str(e)[:80])

    async def test_rtl(self, page):
        try:
            await page.goto(f"{BASE_URL}/dashboard/", timeout=10000)
            await page.wait_for_load_state("domcontentloaded")

            direction = await page.evaluate(
                "() => getComputedStyle(document.body).direction"
            )
            self.record("اتجاه النص (RTL)", "PASS" if direction == "rtl" else "FAIL",
                        f"direction: {direction}")

            body_text = await page.inner_text("body")
            has_arabic = any('\u0600' <= c <= '\u06FF' for c in body_text[:2000])
            self.record("وجود نصوص عربية", "PASS" if has_arabic else "FAIL",
                        f"Arabic chars found: {has_arabic}")

        except Exception as e:
            self.record("RTL/Arabic", "FAIL", str(e)[:100])

    async def test_responsive(self, page, context):
        viewports = [
            (375, 812, "Mobile (iPhone X)"),
            (768, 1024, "Tablet (iPad)"),
            (1920, 1080, "Desktop"),
        ]
        for w, h, label in viewports:
            try:
                await page.set_viewport_size({"width": w, "height": h})
                await page.goto(f"{BASE_URL}/dashboard/", timeout=10000)
                await page.wait_for_load_state("domcontentloaded")

                has_overflow = await page.evaluate(
                    "() => document.body.scrollWidth > window.innerWidth"
                )
                self.record(f"Responsive — {label}",
                            "PASS" if not has_overflow else "FAIL",
                            f"Overflow: {has_overflow}")
            except Exception as e:
                self.record(f"Responsive — {label}", "FAIL", str(e)[:80])

        await page.set_viewport_size({"width": 1920, "height": 1080})

    async def test_forms(self, page):
        try:
            await page.goto(f"{BASE_URL}/sales/invoices/create/", timeout=10000)
            await page.wait_for_load_state("networkidle")

            forms = page.locator("form")
            count = await forms.count()
            self.record("وجود نماذج (Forms)", "PASS" if count > 0 else "FAIL",
                        f"Found {count} forms")

            required = page.locator("[required], .required, .is-required")
            req_count = await required.count()
            self.record("حقول مطلوبة (Required Fields)",
                        "PASS" if req_count > 0 else "FAIL",
                        f"Found {req_count} required fields")

        except Exception as e:
            self.record("Forms Validation", "FAIL", str(e)[:100])

    async def test_search(self, page):
        try:
            await page.goto(f"{BASE_URL}/dashboard/", timeout=10000)
            await page.wait_for_load_state("domcontentloaded")

            search = page.locator(
                'input[type="search"], input[name="q"], input[name="search"], '
                '[class*="search"] input, #search'
            )
            count = await search.count()
            self.record("وجود حقل البحث", "PASS" if count > 0 else "FAIL",
                        f"Found {count} search inputs")

            if count > 0:
                await search.first.fill("test")
                await page.wait_for_timeout(1000)
                self.record("البحث — إدخال نص", "PASS", "Typed 'test'")

        except Exception as e:
            self.record("البحث", "FAIL", str(e)[:100])

    async def test_performance(self, page):
        pages_to_time = [
            ("/dashboard/", "Dashboard"),
            ("/products/", "Products"),
            ("/login/", "Login Page"),
        ]
        for path, name in pages_to_time:
            try:
                start = time.time()
                await page.goto(f"{BASE_URL}{path}", timeout=15000)
                await page.wait_for_load_state("networkidle")
                elapsed = round((time.time() - start) * 1000)

                ok = elapsed < 5000
                self.record(f"سرعة تحميل {name}",
                            "PASS" if ok else "FAIL",
                            f"{elapsed}ms {'✨' if elapsed < 2000 else '⚠️ بطيء' if elapsed > 3000 else ''}")
            except Exception as e:
                self.record(f"سرعة تحميل {name}", "FAIL", str(e)[:80])

    async def test_error_messages(self, page):
        try:
            resp = await page.goto(f"{BASE_URL}/nonexistent-page-xyz/", timeout=10000)
            status = resp.status if resp else 0
            self.record("صفحة 404",
                        "PASS" if status == 404 else "FAIL",
                        f"Status: {status} (expected 404)")

            resp = await page.goto(f"{BASE_URL}/api/products/", timeout=10000)
            status = resp.status if resp else 0
            self.record("API بدون مصادقة",
                        "PASS" if status in (401, 403) else "FAIL",
                        f"Status: {status}")

        except Exception as e:
            self.record("Error Messages", "FAIL", str(e)[:100])

    async def test_accessibility(self, page):
        try:
            await page.goto(f"{BASE_URL}/dashboard/", timeout=10000)
            await page.wait_for_load_state("domcontentloaded")

            images = page.locator("img")
            img_count = await images.count()
            imgs_with_alt = page.locator("img[alt]")
            alt_count = await imgs_with_alt.count()
            if img_count > 0:
                pct = round(alt_count / img_count * 100)
                self.record("صور مع Alt Text",
                            "PASS" if pct >= 80 else "FAIL",
                            f"{alt_count}/{img_count} ({pct}%)")
            else:
                self.record("صور مع Alt Text", "PASS", "No images found")

            meta = page.locator('meta[name="viewport"]')
            has_viewport = await meta.count() > 0
            self.record("Meta Viewport",
                        "PASS" if has_viewport else "FAIL",
                        f"Found: {has_viewport}")

            lang = await page.evaluate(
                "() => document.documentElement.getAttribute('lang')"
            )
            self.record("HTML lang attribute",
                        "PASS" if lang else "FAIL",
                        f"lang='{lang}'")

        except Exception as e:
            self.record("Accessibility", "FAIL", str(e)[:100])

    # ──────────────────────────────────────
    def print_summary(self):
        total = self.passed + self.failed
        pct = round(self.passed / total * 100) if total else 0
        print("\n" + "=" * 60)
        print("📊 ملخص اختبارات UX")
        print("=" * 60)
        print(f"  إجمالي الاختبارات: {total}")
        print(f"  ✅ ناجح: {self.passed}")
        print(f"  ❌ فاشل: {self.failed}")
        print(f"  📈 نسبة النجاح: {pct}%")
        print("=" * 60)

        if pct >= 90:
            print("🏆 ممتاز! تجربة المستخدم رائعة")
        elif pct >= 70:
            print("👍 جيد — بعض التحسينات المطلوبة")
        elif pct >= 50:
            print("⚠️ متوسط — يحتاج تحسينات")
        else:
            print("🔴 يحتاج مراجعة شاملة")


if __name__ == "__main__":
    suite = UXTestSuite()
    asyncio.run(suite.run())
