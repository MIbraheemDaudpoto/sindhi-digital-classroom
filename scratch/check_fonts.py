import asyncio
from playwright.async_api import async_playwright

async def test_font():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('http://127.0.0.1:8000/app/learn')
        await page.wait_for_timeout(2000)
        font_status = await page.evaluate("""() => {
            return {
                bodyFont: window.getComputedStyle(document.body).fontFamily,
                checkMBSindhiWeb: document.fonts.check('16px "MB Sindhi web"'),
                checkMBSindhi: document.fonts.check('16px "MB Sindhi"'),
                fontsList: Array.from(document.fonts).map(f => ({ family: f.family, status: f.status, weight: f.weight }))
            };
        }""")
        print("Font status:", font_status)
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_font())

