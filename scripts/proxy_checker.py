import requests
import asyncio
import aiohttp
import concurrent.futures
from typing import List, Set
import time
import re
import sys
import os

# Add scripts directory to path
sys.path.append(os.path.dirname(__file__))

# Import our fast blacklist checker
from blacklist_checker import FastBlacklistChecker

# Config
MAX_WORKERS = 200  # Increased concurrency
BATCH_SIZE = 1000  # Process in batches
TIMEOUT = 5  # Seconds

class UltraFastProxyChecker:
    def __init__(self):
        self.blacklist_checker = FastBlacklistChecker()
        self.session = None
        
    async def setup_session(self):
        """Setup aiohttp session"""
        self.session = aiohttp.ClientSession()
        
    async def fetch_url(self, url: str) -> List[str]:
        """Fetch proxies from a URL asynchronously"""
        try:
            async with self.session.get(url, timeout=TIMEOUT) as response:
                if response.status == 200:
                    text = await response.text()
                    return [p.strip() for p in text.splitlines() if p.strip()]
        except:
            pass
        return []
    
    async def fetch_all_proxies(self, urls: List[str]) -> Set[str]:
        """Fetch proxies from all URLs concurrently"""
        if not self.session:
            await self.setup_session()
            
        tasks = [self.fetch_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        proxies = set()
        for result in results:
            if isinstance(result, list):
                proxies.update(result)
                
        return proxies
    
    def validate_proxy_format(self, proxy: str) -> bool:
        """Quick validation of proxy format"""
        if not proxy or ':' not in proxy:
            return False
            
        ip, port = proxy.split(':', 1)
        
        # Validate IP format
        if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
            return False
            
        # Validate port
        try:
            port_num = int(port)
            if not 1 <= port_num <= 65535:
                return False
        except:
            return False
            
        return True
    
    def extract_ips(self, proxies: List[str]) -> List[str]:
        """Extract IPs from proxy list"""
        ips = []
        valid_proxies = []
        
        for proxy in proxies:
            if self.validate_proxy_format(proxy):
                ip = proxy.split(':', 1)[0]
                ips.append(ip)
                valid_proxies.append(proxy)
                
        return ips, valid_proxies
    
    def check_proxies_batch(self, proxies: List[str]) -> List[str]:
        """Check a batch of proxies for blacklisting"""
        if not proxies:
            return []
            
        # Extract IPs
        ips, valid_proxies = self.extract_ips(proxies)
        
        if not ips:
            return []
            
        # Check all IPs in batch
        results = self.blacklist_checker.check_multiple_ips(ips)
        
        # Return only clean proxies
        clean_proxies = []
        for proxy, ip in zip(valid_proxies, ips):
            if not results.get(ip, False):
                clean_proxies.append(proxy)
                
        return clean_proxies
    
    async def run(self):
        """Main execution method"""
        start_time = time.time()
        
        # Proxy sources
        proxy_sources = [
            "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/http.txt",
            "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
            "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/http.txt",
        ]
        
        print("Fetching proxies from sources...")
        all_proxies = await self.fetch_all_proxies(proxy_sources)
        print(f"Found {len(all_proxies)} total proxies")
        
        # Convert to list for processing
        proxies_list = list(all_proxies)
        total_proxies = len(proxies_list)
        
        if total_proxies == 0:
            print("No proxies found. Exiting.")
            return []
        
        print(f"Processing {total_proxies} proxies...")
        
        # Process in batches for memory efficiency
        clean_proxies = []
        for i in range(0, total_proxies, BATCH_SIZE):
            batch = proxies_list[i:i + BATCH_SIZE]
            batch_clean = self.check_proxies_batch(batch)
            clean_proxies.extend(batch_clean)
            
            # Progress update
            processed = min(i + BATCH_SIZE, total_proxies)
            elapsed = time.time() - start_time
            speed = processed / elapsed if elapsed > 0 else 0
            
            print(f"Processed: {processed}/{total_proxies} | "
                  f"Valid: {len(clean_proxies)} | "
                  f"Speed: {speed:.1f} proxies/sec")
        
        # Close session
        if self.session:
            await self.session.close()
            
        total_time = time.time() - start_time
        print(f"\nCompleted in {total_time:.2f} seconds")
        print(f"Found {len(clean_proxies)} clean proxies out of {total_proxies}")
        
        return clean_proxies

def main():
    """Main function"""
    print("Starting ultra-fast proxy checker...")
    
    checker = UltraFastProxyChecker()
    clean_proxies = asyncio.run(checker.run())
    
    # Save results
    if clean_proxies:
        with open("clean_proxies.txt", "w") as f:
            f.write("\n".join(clean_proxies))
        print(f"Results saved to clean_proxies.txt")
    else:
        print("No clean proxies found")
    
    print("Proxy check completed!")

if __name__ == "__main__":
    main()
