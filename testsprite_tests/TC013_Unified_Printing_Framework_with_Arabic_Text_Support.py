import asyncio
from playwright import async_api

async def run_test():
    pw = None
    browser = None
    context = None

    try:
        # Start a Playwright session in asynchronous mode
        pw = await async_api.async_playwright().start()

        # Launch a Chromium browser in headless mode with custom arguments
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--window-size=1280,720",         # Set the browser window size
                "--disable-dev-shm-usage",        # Avoid using /dev/shm which can cause issues in containers
                "--ipc=host",                     # Use host-level IPC for better stability
                "--single-process"                # Run the browser in a single process mode
            ],
        )

        # Create a new browser context (like an incognito window)
        context = await browser.new_context()
        context.set_default_timeout(5000)

        # Open a new page in the browser context
        page = await context.new_page()

        # Navigate to your target URL and wait until the network request is committed
        await page.goto("http://localhost:8000/dashboard/dashboard", wait_until="commit", timeout=10000)

        # Wait for the main page to reach DOMContentLoaded state (optional for stability)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=3000)
        except async_api.Error:
            pass

        # Iterate through all iframes and wait for them to load as well
        for frame in page.frames:
            try:
                await frame.wait_for_load_state("domcontentloaded", timeout=3000)
            except async_api.Error:
                pass

        # Interact with the page elements to simulate user flow
        # -> Navigate to http://localhost:8000/dashboard/dashboard
        await page.goto("http://localhost:8000/dashboard/dashboard", wait_until="commit", timeout=10000)
        
        # -> Fill username and password fields and submit the login form to access the dashboard.
        frame = context.pages[-1]
        # Input text
        elem = frame.locator('xpath=html/body/div[1]/div/form/div[1]/input').nth(0)
        await page.wait_for_timeout(3000); await elem.fill('boss')
        
        frame = context.pages[-1]
        # Input text
        elem = frame.locator('xpath=html/body/div[1]/div/form/div[2]/div/input').nth(0)
        await page.wait_for_timeout(3000); await elem.fill('Mm02022006')
        
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=html/body/div[1]/div/form/button').nth(0)
        await page.wait_for_timeout(3000); await elem.click(timeout=5000)
        
        # -> Open the Quick Access / الوصول السريع panel so the POS (نقطة البيع) entry can be clicked and a sales invoice created.
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=html/body/div[3]/nav/div/ul/li[3]/a').nth(0)
        await page.wait_for_timeout(3000); await elem.click(timeout=5000)
        
        # -> Use the global feature search to find 'نقطة البيع' (POS) and open it so a sales invoice can be created for the thermal receipt test.
        frame = context.pages[-1]
        # Input text
        elem = frame.locator('xpath=html/body/div[2]/div[2]/div/input').nth(0)
        await page.wait_for_timeout(3000); await elem.fill('نقطة البيع')
        
        # -> Click the 'نقاط البيع' (POS) entry in the sidebar to open the POS module so a sales invoice can be created for the thermal receipt test.
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=html/body/div[2]/div[3]/ul/li[18]/button').nth(0)
        await page.wait_for_timeout(3000); await elem.click(timeout=5000)
        
        # -> Click the 'نقاط البيع' entry inside the quick-access/flyout to open the POS module so a sales invoice can be created for the thermal receipt test.
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=html/body/div[9]/div[3]/a[2]').nth(0)
        await page.wait_for_timeout(3000); await elem.click(timeout=5000)
        
        # -> Add a product to the cart (click the RBAC Product entry) so the order total updates and payment/print controls appear.
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=html/body/div[3]/main/div/div[1]/div[2]/div[1]/div[2]/div/div[2]/div[3]').nth(0)
        await page.wait_for_timeout(3000); await elem.click(timeout=5000)
        
        # -> Click the 'RBAC Product' product tile again (index 27489) to add it to the cart so the payment/print controls appear.
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=html/body/div[3]/main/div/div[1]/div[2]/div[1]/div[2]/div/div[2]/div[3]').nth(0)
        await page.wait_for_timeout(3000); await elem.click(timeout=5000)
        
        # -> Open the cart/order area to access payment controls (open payment modal) so the sales invoice can be paid and a thermal receipt printed.
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=html/body/div[3]/main/div/div[1]/div[2]/div[2]/div[2]/div').nth(0)
        await page.wait_for_timeout(3000); await elem.click(timeout=5000)
        
        # -> Open the payment modal / trigger payment flow so the thermal receipt print option appears (click the most relevant control to start payment).
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=html/body/div[3]/main/div/div[1]/div[2]/div[2]/div[3]/div[4]/span[1]/i').nth(0)
        await page.wait_for_timeout(3000); await elem.click(timeout=5000)
        
        # -> Click the 'الدفع' (pay) button to open the payment modal so the thermal receipt print option appears.
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=html/body/div[3]/main/div/div[1]/div[2]/div[2]/div[3]/div[5]/div[1]/button[1]').nth(0)
        await page.wait_for_timeout(3000); await elem.click(timeout=5000)
        
        # -> Click 'تأكيد الدفع' (Confirm Payment) to finalize the sale and trigger the thermal receipt print (XPrinter). After click, observe confirmation/success and then proceed to ZPL label printing.
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=html/body/div[3]/main/div/div[3]/div/div/div[3]/button[2]').nth(0)
        await page.wait_for_timeout(3000); await elem.click(timeout=5000)
        
        # --> Assertions to verify final state
        frame = context.pages[-1]
        try:
            await expect(frame.locator('text=تمت طباعة الإيصال بنجاح').first).to_be_visible(timeout=3000)
        except AssertionError:
            raise AssertionError("Test case failed: Expected a confirmation that the thermal receipt was printed with correct RTL Arabic text ('تمت طباعة الإيصال بنجاح'). The confirmation did not appear — printing may have failed or Arabic rendering/layout is incorrect.")
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    