import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    target_url = "https://www.dsmartgo.com.tr/tr/tv-izle/szc-tv/246240"
    m3u8_link = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        async def handle_request(request):
            nonlocal m3u8_link
            if ".m3u8" in request.url and "ercdn.net" in request.url:
                m3u8_link = request.url

        page.on("request", handle_request)

        try:
            print("Loading page to extract tokenized URL...")
            await page.goto(target_url, wait_until="networkidle")
            await page.wait_for_timeout(5000) 
        except Exception as e:
            print(f"Error loading page: {e}")
        finally:
            await browser.close()
            
    if m3u8_link:
        print(f"Successfully grabbed new stream: {m3u8_link}")
        file_path = "main.m3u"
        
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            channel_found = False
            for i in range(len(lines)):
                if 'tvg-id="SozcuTV.tr"' in lines[i]:
                    if i + 1 < len(lines):
                        lines[i + 1] = f"{m3u8_link}\n"
                        channel_found = True
                        break
            
            if channel_found:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                print("Successfully updated main.m3u with the new link.")
            else:
                print("Could not find the tvg-id='SozcuTV.tr' line in main.m3u.")
        else:
            print(f"Error: {file_path} not found in the repository.")
    else:
        print("Could not find the m3u8 link during scraping.")

if __name__ == "__main__":
    asyncio.run(main())
