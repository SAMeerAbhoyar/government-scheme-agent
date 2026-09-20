import os
import sys
import yaml
import asyncio
import httpx

# Ensure backend directory is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(script_dir, "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

SOURCES_FILE = os.path.join(backend_dir, "app", "ingestion", "sources.yaml")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

async def check_single_source(client: httpx.AsyncClient, source: dict):
    s_id = source.get("id", "unknown")
    url = source.get("url", "")
    s_type = source.get("type", "html")

    headers = {"User-Agent": USER_AGENT}
    try:
        response = await client.get(url, headers=headers, follow_redirects=True, timeout=15.0)
        status = response.status_code
        content_type = response.headers.get("content-type", "unknown").split(";")[0].strip()
        size_bytes = len(response.content)
        size_str = f"{size_bytes / 1024:.1f} KB" if size_bytes > 0 else "0 KB"
        
        print(f"[{s_id:30s}] STATUS: {status:3d} | TYPE: {content_type:30s} | SIZE: {size_str:10s} | URL: {url}")
        return {"id": s_id, "url": url, "status": status, "content_type": content_type, "size": size_bytes, "ok": status < 400}
    except Exception as e:
        err_msg = type(e).__name__
        print(f"[{s_id:30s}] STATUS: FAIL ({err_msg}) | URL: {url}")
        return {"id": s_id, "url": url, "status": "FAIL", "error": err_msg, "ok": False}

async def main():
    if not os.path.exists(SOURCES_FILE):
        print(f"Error: Sources file not found at {SOURCES_FILE}")
        sys.exit(1)

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    sources = config.get("sources", [])
    print(f"Checking {len(sources)} source URLs from sources.yaml...\n" + "=" * 100)

    async with httpx.AsyncClient(verify=False) as client:
        tasks = [check_single_source(client, src) for src in sources]
        results = await asyncio.gather(*tasks)

    print("=" * 100)
    successful = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]]
    print(f"\nSOURCE CHECK SUMMARY:")
    print(f"  Total URLs Checked: {len(results)}")
    print(f"  Reachable (2xx/3xx): {len(successful)}")
    print(f"  Failed / Dead:      {len(failed)}")

if __name__ == "__main__":
    asyncio.run(main())
