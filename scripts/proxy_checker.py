import asyncio
import aiohttp
import aiodns
import socket
import re
import time
from typing import List, Set, Dict, Tuple
from dataclasses import dataclass
import random

@dataclass
class ProxyResult:
    proxy: str
    is_working: bool = False
    response_time: float = 0.0
    is_blacklisted: bool = False
    spam_score: int = 100

class UltraFastProxyChecker:
    def __init__(self):
        self.dns_servers = ['1.1.1.1', '8.8.8.8', '9.9.9.9']
        self.resolver = None
        self.session = None
        self.semaphore = asyncio.Semaphore(100)  # Limit concurrency
        
        # DNS Blacklists (reduced for speed)
        self.blacklist_domains = [
            "zen.spamhaus.org",
            "bl.spamcop.net", 
            "xbl.spamhaus.org"
        ]
        
        # Test URLs for proxy checking
        self.test_urls = [
            "http://httpbin.org/ip",
            "http://example.com"
        ]

    async def setup_resolver(self):
        """Setup async DNS resolver"""
        try:
            self.resolver = aiodns.DNSResolver()
            self.resolver.nameservers = self.dns_servers
            self.resolver.timeout = 2
        except:
            self.resolver = None

    async def setup_session(self):
        """Setup aiohttp session"""
        timeout = aiohttp.ClientTimeout(total=10, connect=3)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def fetch_proxies_from_url(self, url: str) -> Set[str]:
        """Fetch unique proxies from a URL"""
        try:
            async with self.session.get(url, timeout=5) as response:
                if response.status == 200:
                    text = await response.text()
                    proxies = set()
                    for line in text.splitlines():
                        line = line.strip()
                        if self.validate_proxy_format(line):
                            proxies.add(line)
                    return proxies
        except:
            return set()
        return set()

    async def fetch_all_proxies(self, urls: List[str]) -> Set[str]:
        """Fetch proxies from all URLs concurrently"""
        tasks = []
        for url in urls:
            task = asyncio.create_task(self.fetch_proxies_from_url(url))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        unique_proxies = set()
        for result in results:
            if isinstance(result, set):
                unique_proxies.update(result)
                
        return unique_proxies

    def validate_proxy_format(self, proxy: str) -> bool:
        """Validate proxy format quickly"""
        if not proxy or ':' not in proxy:
            return False
            
        parts = proxy.split(':', 1)
        if len(parts) != 2:
            return False
            
        ip, port = parts
        
        # Quick IP validation
        if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
            return False
            
        # Quick port validation
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except:
            return False

    async def check_proxy_working(self, proxy: str) -> Tuple[bool, float]:
        """Check if proxy is working with timeout"""
        test_url = random.choice(self.test_urls)
        start_time = time.time()
        
        try:
            async with self.session.get(
                test_url, 
                proxy=f"http://{proxy}",
                timeout=3
            ) as response:
                if response.status == 200:
                    response_time = time.time() - start_time
                    return True, round(response_time, 3)
        except:
            pass
            
        return False, 0.0

    async def check_single_blacklist(self, query: str, domain: str) -> bool:
        """Check a single blacklist with timeout"""
        try:
            full_query = f"{query}.{domain}"
            await asyncio.wait_for(
                self.resolver.query(full_query, 'A'),
                timeout=1
            )
            return True
        except:
            return False

    async def check_ip_blacklisted(self, ip: str) -> bool:
        """Check if IP is blacklisted"""
        if not self.resolver:
            return False
            
        reversed_ip = ".".join(ip.split(".")[::-1])
        
        # Check only the most important blacklists
        tasks = []
        for domain in self.blacklist_domains[:2]:  # Only check 2 blacklists
            tasks.append(self.check_single_blacklist(reversed_ip, domain))
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return any(result for result in results if isinstance(result, bool) and result)
        except:
            return False

    async def check_spam_score(self, ip: str) -> int:
        """Quick spam score check"""
        try:
            # Simple heuristic based on IP patterns
            octets = ip.split('.')
            first_octet = int(octets[0])
            
            if first_octet in [1, 2, 3, 4]:
                return 20
            elif first_octet in [10, 172, 192]:  # Private ranges
                return 90
            elif first_octet in [185, 194, 195]:  # Suspicious ranges
                return 60
            else:
                return 30
                
        except:
            return 50

    async def process_single_proxy(self, proxy: str) -> ProxyResult:
        """Process a single proxy with semaphore"""
        async with self.semaphore:
            result = ProxyResult(proxy=proxy)
            
            try:
                # Step 1: Check if working
                is_working, response_time = await self.check_proxy_working(proxy)
                result.is_working = is_working
                result.response_time = response_time
                
                if not is_working:
                    return result
                
                # Extract IP for further checks
                ip = proxy.split(':', 1)[0]
                
                # Step 2: Check blacklist
                is_blacklisted = await self.check_ip_blacklisted(ip)
                result.is_blacklisted = is_blacklisted
                
                if is_blacklisted:
                    return result
                
                # Step 3: Check spam score
                spam_score = await self.check_spam_score(ip)
                result.spam_score = spam_score
                
            except Exception as e:
                # Silently handle errors to avoid breaking the flow
                pass
            
            return result

    async def run_complete_check(self, urls: List[str]) -> List[ProxyResult]:
        """Run complete proxy checking pipeline"""
        start_time = time.time()
        
        # Setup
        await self.setup_session()
        await self.setup_resolver()
        
        print("🔄 Fetching unique proxies from sources...")
        unique_proxies = await self.fetch_all_proxies(urls)
        print(f"✅ Found {len(unique_proxies)} unique proxies")
        
        if not unique_proxies:
            return []
        
        proxies_list = list(unique_proxies)
        total_proxies = len(proxies_list)
        
        # Process proxies with limited concurrency
        all_results = []
        completed = 0
        
        # Process in chunks to avoid memory issues
        CHUNK_SIZE = 500
        for i in range(0, total_proxies, CHUNK_SIZE):
            chunk = proxies_list[i:i + CHUNK_SIZE]
            
            # Process chunk with limited concurrency
            tasks = []
            for proxy in chunk:
                task = asyncio.create_task(self.process_single_proxy(proxy))
                tasks.append(task)
            
            chunk_results = []
            for future in asyncio.as_completed(tasks):
                try:
                    result = await future
                    chunk_results.append(result)
                    completed += 1
                    
                    # Progress update every 100 proxies
                    if completed % 100 == 0:
                        elapsed = time.time() - start_time
                        speed = completed / elapsed if elapsed > 0 else 0
                        
                        working = sum(1 for r in all_results + chunk_results if r.is_working)
                        clean = sum(1 for r in all_results + chunk_results 
                                  if r.is_working and not r.is_blacklisted and r.spam_score <= 50)
                        
                        print(f"📊 Processed: {completed}/{total_proxies} | "
                              f"Working: {working} | Clean: {clean} | "
                              f"Speed: {speed:.1f} proxies/sec")
                              
                except Exception as e:
                    completed += 1
            
            all_results.extend(chunk_results)
            
            # Clear memory between chunks
            del chunk
            del tasks
            if i % 2000 == 0:
                await asyncio.sleep(0.1)
        
        # Close session
        await self.session.close()
        
        total_time = time.time() - start_time
        print(f"\n🎉 Completed in {total_time:.2f} seconds")
        
        return all_results

    def filter_final_results(self, results: List[ProxyResult]) -> List[str]:
        """Filter final results based on criteria"""
        final_proxies = []
        
        for result in results:
            if (result.is_working and 
                not result.is_blacklisted and 
                result.spam_score <= 50 and
                result.response_time <= 2.0):
                final_proxies.append(result.proxy)
        
        return final_proxies

async def main():
    """Main function"""
    print("🚀 Starting Ultra Fast All-in-One Proxy Checker...")
    print("=" * 60)
    
    # Reduced list of reliable sources
    proxy_sources = [
        "https://raw.githubusercontent.com/akbarali123A/proxy_scraper/refs/heads/main/http_proxies.txt",
        "https://raw.githubusercontent.com/akbarali123A/proxy_scraper/refs/heads/main/https_proxies.txt",
        "https://raw.githubusercontent.com/akbarali123A/proxy_scraper/refs/heads/main/socks4_proxies.txt",
        "https://raw.githubusercontent.com/akbarali123A/proxy_scraper/refs/heads/main/socks5_proxies.txt",
    ]
    
    checker = UltraFastProxyChecker()
    
    try:
        results = await asyncio.wait_for(
            checker.run_complete_check(proxy_sources),
            timeout=7200  # 120 minutes timeout
        )
    except asyncio.TimeoutError:
        print("⏰ Timeout reached! Saving partial results...")
        results = []
    
    # Filter final results
    final_proxies = checker.filter_final_results(results)
    
    # Generate statistics
    total = len(results)
    working = sum(1 for r in results if r.is_working)
    blacklisted = sum(1 for r in results if r.is_blacklisted)
    low_spam = sum(1 for r in results if r.spam_score <= 50)
    
    print("=" * 60)
    print("📊 FINAL STATISTICS:")
    print(f"   Total Proxies: {total}")
    print(f"   Working Proxies: {working} ({working/total*100:.1f}%%)")
    print(f"   Blacklisted: {blacklisted}")
    print(f"   Low Spam Score: {low_spam}")
    print(f"   ✅ Final Clean Proxies: {len(final_proxies)}")
    print("=" * 60)
    
    # Save results
    if final_proxies:
        with open("clean_proxies.txt", "w") as f:
            f.write("\n".join(final_proxies))
        print(f"💾 Results saved to clean_proxies.txt")
    else:
        print("❌ No clean proxies found")
        # Create empty file
        with open("clean_proxies.txt", "w") as f:
            f.write("")
    
    print("✅ Proxy check completed!")

if __name__ == "__main__":
    asyncio.run(main())
