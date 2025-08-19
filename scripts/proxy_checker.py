import requests
import subprocess
import os
import concurrent.futures
from datetime import datetime
import hashlib

# Config
MAX_WORKERS = 50
BLACKLIST_THRESHOLD = 70
GITHUB_REPO = "https://github.com/fredycibersec/ip-blacklist-checker"
LOCAL_CHECKER_DIR = "ip-blacklist-checker"

def setup_blacklist_checker():
    """Setup the blacklist checker tool"""
    if not os.path.exists(LOCAL_CHECKER_DIR):
        print("Cloning blacklist checker...")
        subprocess.run(["git", "clone", GITHUB_REPO, LOCAL_CHECKER_DIR], 
                      check=True, capture_output=True)
        print("Blacklist checker setup complete")

def fetch_proxies(urls):
    """Fetch proxies from GitHub raw URLs"""
    proxies = set()
    for url in urls:
        try:
            print(f"Fetching from: {url}")
            res = requests.get(url, timeout=15)
            if res.status_code == 200:
                new_proxies = [p.strip() for p in res.text.splitlines() if p.strip()]
                proxies.update(new_proxies)
                print(f"Found {len(new_proxies)} proxies from {url}")
            else:
                print(f"Failed to fetch {url}: Status {res.status_code}")
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            continue
    return list(proxies)

def run_blacklist_check(ip):
    """Check if IP is blacklisted using local tool"""
    try:
        result = subprocess.run(
            ["python", f"{LOCAL_CHECKER_DIR}/checker.py", ip],
            capture_output=True,
            text=True,
            timeout=8
        )
        return "BLACKLISTED" in result.stdout
    except subprocess.TimeoutExpired:
        print(f"Timeout checking IP: {ip}")
        return True
    except Exception as e:
        print(f"Error checking IP {ip}: {e}")
        return True

def check_proxy(proxy):
    """Check individual proxy"""
    try:
        ip = proxy.split(":")[0].strip()
        if not ip:
            return None
            
        if run_blacklist_check(ip):
            return None
            
        return proxy
    except Exception as e:
        print(f"Error processing proxy {proxy}: {e}")
        return None

def main():
    """Main function"""
    print("Starting proxy checker...")
    
    # Setup blacklist checker
    setup_blacklist_checker()
    
    # Proxy sources
    proxy_sources = [
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
       
    ]
    
    # Fetch proxies
    print("Fetching proxies from sources...")
    proxies = fetch_proxies(proxy_sources)
    print(f"Total unique proxies found: {len(proxies)}")
    
    if not proxies:
        print("No proxies found. Exiting.")
        return
    
    # Check proxies
    print("Checking proxies for blacklisting...")
    valid_proxies = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_proxy, proxy): proxy for proxy in proxies}
        
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            result = future.result()
            if result:
                valid_proxies.append(result)
            
            # Progress update
            if i % 1000 == 0 or i == len(proxies):
                print(f"Checked {i}/{len(proxies)} proxies | Valid: {len(valid_proxies)}")
    
    # Save results
    print(f"Saving {len(valid_proxies)} valid proxies...")
    with open("clean_proxies.txt", "w") as f:
        f.write("\n".join(valid_proxies))
    
    print("Proxy check completed successfully!")

if __name__ == "__main__":
    main()
