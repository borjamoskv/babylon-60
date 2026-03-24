import argparse
import asyncio

from playwright.async_api import async_playwright


async def run(target_url: str, port: int):
    async with async_playwright() as p:
        try:
            # Connect to existing Chrome over CDP
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
            contexts = browser.contexts

            found = False
            for context in contexts:
                for page in context.pages:
                    if target_url in page.url:
                        found = True
                        title = await page.title()
                        print(f"[*] Found target tab: {page.url} ({title})")
                        content = await page.content()

                        # Output to stdout or save to file
                        print(f"[*] Extracted {len(content)} bytes of HTML.")
                        print(content[:500] + "\n...[truncated]...")

                        # Save it for CORTEX
                        safe_name = target_url.replace("/", "_").replace(".", "_")
                        out_path = f"/tmp/extracted_dom_{safe_name}.html"
                        with open(out_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        print(f"[+] Full DOM saved to {out_path}")
                        break
                if found:
                    break

            if not found:
                print(f"[-] No open tab found matching URL pattern: '{target_url}'.")
                print("[-] Make sure Chrome is open and running with --remote-debugging-port=9222")

        except Exception as e:
            print(f"[!] Error connecting to CDP on port {port}: {e}")
            print(f"[!] Please ensure Google Chrome was launched with --remote-debugging-port={port}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract DOM from Chrome via CDP")
    parser.add_argument("target_url", help="URL pattern to match in open tabs")
    parser.add_argument("--port", type=int, default=9222, help="CDP Port")
    args = parser.parse_args()

    asyncio.run(run(args.target_url, args.port))
