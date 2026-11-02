import asyncio
from playwright.async_api import async_playwright

async def test_elements():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('http://127.0.0.1:8000/app/learn')
        await page.wait_for_timeout(2000)
        
        elements_info = await page.evaluate("""() => {
            const results = [];
            const tags = ['body', 'h1', 'h2', 'h3', 'p', 'button', 'input', '.lms-sidebar', '.video-title', '.chat-message'];
            for (const selector of tags) {
                const el = document.querySelector(selector);
                if (el) {
                    const style = window.getComputedStyle(el);
                    results.push({ selector, fontFamily: style.fontFamily });
                }
            }
            return results;
        }""")
        for item in elements_info:
            print(item)
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_elements())

