import asyncio
import aiohttp
import async_timeout
from typing import List, Set, Dict
import time
import re
import os
import random

# Import our fast blacklist checker
from blacklist_checker import UltraFastBlacklistChecker

# Config
MAX_CONCURRENT_DNS = 500
MAX_CONCURRENT_HTTP = 100
BATCH_SIZE = 1000
TIMEOUT = 10

class CompleteProxyChecker:
    def __init__(self):
        self.blacklist_checker = UltraFastBlacklistChecker()
        self.session = None
        self.working_proxies = []
        
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
    
    async def check_proxy_working(self, proxy: str) -> bool:
        """Check if proxy is actually working by making a test request"""
        test_urls = [
            "http://httpbin.org/ip",
            "http://api.ipify.org",
            "http://icanhazip.com"
        ]
        
        test_url = random.choice(test_urls)
        
        try:
            async with async_timeout.timeout(TIMEOUT):
                async with self.session.get(
                    test_url,
                    proxy=f"http://{proxy}",
                    timeout=TIMEOUT
                ) as response:
                    if response.status == 200:
                        # Verify we actually got an IP response
                        text = await response.text()
                        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', text.strip()):
                            return True
        except:
            pass
            
        return False
    
    async def check_working_proxies(self, proxies: List[str]) -> List[str]:
        """Check which proxies are actually working"""
        working = []
        tasks = []
        
        for proxy in proxies:
            tasks.append(self.check_proxy_working(proxy))
        
        # Process in smaller batches to avoid overwhelming
        for i in range(0, len(tasks), MAX_CONCURRENT_HTTP):
            batch_tasks = tasks[i:i + MAX_CONCURRENT_HTTP]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for proxy, is_working in zip(proxies[i:i + MAX_CONCURRENT_HTTP], batch_results):
                if is_working and not isinstance(is_working, Exception):
                    working.append(proxy)
            
            print(f"Working check: {min(i + MAX_CONCURRENT_HTTP, len(proxies))}/{len(proxies)} | Working: {len(working)}")
        
        return working
    
    async def check_proxies_blacklist(self, proxies: List[str]) -> List[str]:
        """Check proxies for blacklisting"""
        if not proxies:
            return []
            
        # Extract IPs
        ips, valid_proxies = self.extract_ips(proxies)
        
        if not ips:
            return []
            
        # Check all IPs in batch using async
        results = await self.blacklist_checker.check_multiple_ips(ips)
        
        # Return only clean proxies
        clean_proxies = []
        for proxy, ip in zip(valid_proxies, ips):
            if not results.get(ip, False):
                clean_proxies.append(proxy)
                
        return clean_proxies
    
    async def run(self):
        """Main execution method - Complete pipeline"""
        start_time = time.time()
        
        # Proxy sources
        proxy_sources = [
            "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/http.txt",
            "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
            "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/http.txt",
            "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list.txt",
            "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt",
        ]
        
        print("=== STAGE 1: Fetching proxies from sources ===")
        all_proxies = await self.fetch_all_proxies(proxy_sources)
        print(f"Found {len(all_proxies)} total proxies")
        
        # Convert to list and remove duplicates
        unique_proxies = list(all_proxies)
        print(f"After deduplication: {len(unique_proxies)} unique proxies")
        
        if len(unique_proxies) == 0:
            print("No proxies found. Exiting.")
            return []
        
        print("\n=== STAGE 2: Validating proxy format ===")
        valid_format_proxies = [p for p in unique_proxies if self.validate_proxy_format(p)]
        print(f"Valid format: {len(valid_format_proxies)} proxies")
        
        print("\n=== STAGE 3: Checking working proxies ===")
        working_proxies = await self.check_working_proxies(valid_format_proxies)
        print(f"Working proxies: {len(working_proxies)}")
        
        if len(working_proxies) == 0:
            print("No working proxies found. Exiting.")
            return []
        
        print("\n=== STAGE 4: Checking blacklisted proxies ===")
        final_proxies = await self.check_proxies_blacklist(working_proxies)
        print(f"Clean proxies (not blacklisted): {len(final_proxies)}")
        
        # Close session
        if self.session:
            await self.session.close()
            
        total_time = time.time() - start_time
        print(f"\n=== COMPLETED ===")
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Final clean working proxies: {len(final_proxies)}")
        
        return final_proxies

async def main():
    """Main async function"""
    print("Starting complete proxy checker pipeline...")
    print("This will:")
    print("1. Fetch proxies from multiple sources")
    print("2. Remove duplicates")
    print("3. Validate proxy format")
    print("4. Check which proxies are actually working")
    print("5. Remove blacklisted proxies")
    print("6. Save final clean working proxies\n")
    
    checker = CompleteProxyChecker()
    final_proxies = await checker.run()
    
    # Save results
    if final_proxies:
        with open("clean_proxies.txt", "w") as f:
            f.write("\n".join(final_proxies))
        print(f"Results saved to clean_proxies.txt")
        
        # Show sample of results
        print("\nSample of clean working proxies:")
        for proxy in final_proxies[:10]:
            print(f"  {proxy}")
    else:
        print("No clean working proxies found")
    
    print("\nProxy check completed!")

if __name__ == "__main__":
    asyncio.run(main())
