import asyncio
from playwright import async_api
from playwright.async_api import expect

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
        context.set_default_timeout(30000)
        
        # Open a new page in the browser context
        page = await context.new_page()
        
        # Navigate to your target URL and wait until the network request is committed
        await page.goto("http://localhost:8000", wait_until="commit", timeout=30000)
        
        # Wait for the main page to reach DOMContentLoaded state (optional for stability)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
        except async_api.Error:
            pass
        
        # Iterate through all iframes and wait for them to load as well
        for frame in page.frames:
            try:
                await frame.wait_for_load_state("domcontentloaded", timeout=10000)
            except async_api.Error:
                pass
        
        # Interact with the page elements to simulate user flow
        # -> Click on the login link to navigate to the login page
        # Navigate directly to login page to avoid header issues
        await page.goto("http://localhost:8000/accounts/login/", wait_until="commit", timeout=30000)
        
        # -> Input valid username and password, then submit the login form
        # Input valid username 'tony' in the email field
        elem = page.locator('#username')
        await page.wait_for_timeout(3000); await elem.fill('tony')
        

        # -> Input valid password 'Test123!' in the password field
        elem = page.locator('#password')
        await page.wait_for_timeout(3000); await elem.fill('Test123!')
        
        # Click the login button to submit credentials
        elem = page.locator('.btn-login')
        await page.wait_for_timeout(3000); await elem.click()
        
        # -> Correct the username to a valid email format and retry login submission
        # Correct username to valid email format 'tony@example.com'
        elem = page.locator('#username')
        await page.wait_for_timeout(3000); await elem.fill('tony@example.com')
        
        # Click the login button to submit corrected credentials
        elem = page.locator('.btn-login')
        await page.wait_for_timeout(3000); await elem.click()
        
        # -> Input valid username 'boss' and password 'Mm02022006' and submit login form
        # Input valid username 'boss' in the email field
        elem = page.locator('#username')
        await page.wait_for_timeout(3000); await elem.fill('boss')
        
        # Input valid password 'Mm02022006' in the password field
        elem = page.locator('#password')
        await page.wait_for_timeout(3000); await elem.fill('Mm02022006')
        
        # Click the login button to submit valid credentials
        elem = page.locator('.btn-login')
        await page.wait_for_timeout(3000); await elem.click()
        
        # -> Input valid email format username 'boss@example.com' and password 'Mm02022006' and submit login form
        # Input valid email format username 'boss@example.com'
        elem = page.locator('#username')
        await page.wait_for_timeout(3000); await elem.fill('boss@example.com')
        
        # Input valid password 'Mm02022006'
        elem = page.locator('#password')
        await page.wait_for_timeout(3000); await elem.fill('Mm02022006')
        
        # Click the login button to submit credentials
        elem = page.locator('.btn-login')
        await page.wait_for_timeout(3000); await elem.click()
        
        # -> Verify that the dashboard displays modules according to the user's role permissions
        # Click on 'حسابي' (My Account) to check user role and accessible modules
        elem = page.locator('xpath=html/body/footer/div/div/div[3]/div/ul/li/a').nth(0)
        await page.wait_for_timeout(3000); await elem.click()
        
        # --> Assertions to verify final state
        await expect(page.locator('text=لوحة حساب العميل').first).to_be_visible(timeout=30000)
        await expect(page.locator('text=boss').first).to_be_visible(timeout=30000)
        await expect(page.locator('text=إدارة بياناتك، الطلبات، وقائمة الرغبات.').first).to_be_visible(timeout=30000)
        await expect(page.locator('text=boss@example.com').first).to_be_visible(timeout=30000)
        await expect(page.locator('text=غير محدد').first).to_be_visible(timeout=30000)
        await asyncio.sleep(5)
    
    except Exception as e:
        print(f"Test failed: {e}")
        if page:
            try:
                content = await page.content()
                print("Page Content:")
                print(content[:1000]) # Print first 1000 chars
            except:
                pass
        raise e
    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()
            
asyncio.run(run_test())