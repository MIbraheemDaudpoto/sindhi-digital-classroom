import asyncio
from playwright.async_api import async_playwright

async def test_bold():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('http://127.0.0.1:8000/app/learn')
        await page.wait_for_timeout(2000)
        
        bold_check = await page.evaluate("""() => {
            const el = document.createElement('div');
            el.style.fontFamily = 'var(--font-sindhi)';
            el.style.fontWeight = '700';
            el.innerText = 'سنڌي ڊجيٽل ڪلاس روم چيڪنگ';
            document.body.appendChild(el);
            
            return {
                checkBoldMBSindhiWeb: document.fonts.check('bold 16px "MB Sindhi web"'),
                check700MBSindhiWeb: document.fonts.check('700 16px "MB Sindhi web"'),
                check400MBSindhiWeb: document.fonts.check('400 16px "MB Sindhi web"'),
            };
        }""")
        print("Bold check:", bold_check)
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_bold())

