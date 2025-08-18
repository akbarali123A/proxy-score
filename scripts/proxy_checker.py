import requests
import subprocess
import os
import concurrent.futures
from datetime import datetime
import sqlite3
import hashlib

# Config
MAX_WORKERS = 50
BLACKLIST_THRESHOLD = 70
GITHUB_REPO = "https://github.com/fredycibersec/ip-blacklist-checker"
LOCAL_CHECKER_DIR = "ip-blacklist-checker"

def setup_blacklist_checker():
    if not os.path.exists(LOCAL_CHECKER_DIR):
        subprocess.run(["git", "clone", GITHUB_REPO, LOCAL_CHECKER_DIR], check=True)

def fetch_proxies(urls):
    proxies = set()
    for url in urls:
        try:
            res = requests.get(url, timeout=10)
            proxies.update(res.text.splitlines())
        except:
            continue
    return list(proxies)

def run_blacklist_check(ip):
    try:
        result = subprocess.run(
            ["python", f"{LOCAL_CHECKER_DIR}/checker.py", ip],
            capture_output=True,
            text=True,
            timeout=5
        )
        return "BLACKLISTED" in result.stdout
    except:
        return True  # Assume worst if check fails

def check_proxy(proxy):
    ip = proxy.split(":")[0]
    if run_blacklist_check(ip):
        return None
    return proxy  # Only returns if proxy is clean

def main():
    setup_blacklist_checker()
    
    proxy_sources = [
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    ]
    
    print("Fetching proxies...")
    proxies = fetch_proxies(proxy_sources)
    print(f"Total proxies: {len(proxies)}")
    
    print("Checking proxies...")
    valid_proxies = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(check_proxy, proxies)
        valid_proxies = [p for p in results if p]
    
    print(f"Valid proxies: {len(valid_proxies)}")
    with open("clean_proxies.txt", "w") as f:
        f.write("\n".join(valid_proxies))

if __name__ == "__main__":
    main()
