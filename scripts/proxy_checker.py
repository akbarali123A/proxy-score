import asyncio
import aiohttp
import aiodns
import socket
import re
import time
from typing import List, Set, Dict, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import urllib.parse

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
        self.results: Dict[str, ProxyResult] = {}
        
        # DNS Blacklists
        self.blacklist_domains = [
            "zen.spamhaus.org", "bl.spamcop.net", "dnsbl.sorbs.net",
            "xbl.spamhaus.org", "pbl.spamhaus.org", "dnsbl-1.uceprotect.net",
            "b.barracudacentral.org", "dnsbl.io", "rbl.megarbl.net"
        ]
        
        # Test URLs for proxy checking
        self.test_urls = [
            "http://httpbin.org/ip",
            "http://httpbin.org/get",
            "http://example.com"
        ]

    async def setup_resolver(self):
        """Setup async DNS resolver"""
        self.resolver = aiodns.DNSResolver()
        self.resolver.nameservers = self.dns_servers

    async def setup_session(self):
        """Setup aiohttp session"""
        self.session = aiohttp.ClientSession()

    async def fetch_proxies_from_url(self, url: str) -> Set[str]:
        """Fetch unique proxies from a URL"""
        try:
            async with self.session.get(url, timeout=10) as response:
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
        tasks = [self.fetch_proxies_from_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        unique_proxies = set()
        for result in results:
            if isinstance(result, set):
                unique_proxies.update(result)
                
        return unique_proxies

    def validate_proxy_format(self, proxy: str) -> bool:
        """Validate proxy format"""
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

    async def check_proxy_working(self, proxy: str) -> Tuple[bool, float]:
        """Check if proxy is working and measure response time"""
        test_url = "http://httpbin.org/ip"
        start_time = time.time()
        
        try:
            async with self.session.get(
                test_url, 
                proxy=f"http://{proxy}",
                timeout=5
            ) as response:
                if response.status == 200:
                    response_time = time.time() - start_time
                    return True, response_time
        except:
            pass
            
        return False, 0.0

    async def check_single_blacklist(self, query: str, domain: str) -> bool:
        """Check a single blacklist"""
        try:
            full_query = f"{query}.{domain}"
            await self.resolver.query(full_query, 'A')
            return True
        except:
            return False

    async def check_ip_blacklisted(self, ip: str) -> bool:
        """Check if IP is blacklisted"""
        if not self.resolver:
            await self.setup_resolver()
            
        reversed_ip = ".".join(ip.split(".")[::-1])
        
        tasks = []
        for domain in self.blacklist_domains:
            tasks.append(self.check_single_blacklist(reversed_ip, domain))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return any(results)

    async def check_spam_score(self, ip: str) -> int:
        """Check spam score using multiple techniques"""
        try:
            # Method 1: Check common spam patterns
            if ip.startswith(('1.', '2.', '3.')):
                score = 20
            elif re.match(r'^10\.|^172\.(1[6-9]|2[0-9]|3[0-1])\.|^192\.168\.', ip):
                score = 80  # Private IPs get higher score
            else:
                score = 30
                
            # Method 2: Check if IP is in suspicious ranges
            if ip.startswith(('185.', '194.', '195.')):
                score += 20
                
            return min(score, 100)
            
        except:
            return 100

    async def process_proxy_batch(self, proxies: List[str]) -> List[ProxyResult]:
        """Process a batch of proxies"""
        batch_results = []
        
        for proxy in proxies:
            result = ProxyResult(proxy=proxy)
            
            # Extract IP for blacklist checking
            ip = proxy.split(':', 1)[0]
            
            try:
                # Step 1: Check if working
                is_working, response_time = await self.check_proxy_working(proxy)
                result.is_working = is_working
                result.response_time = response_time
                
                if not is_working:
                    batch_results.append(result)
                    continue
                
                # Step 2: Check blacklist (concurrently for working proxies)
                is_blacklisted = await self.check_ip_blacklisted(ip)
                result.is_blacklisted = is_blacklisted
                
                if is_blacklisted:
                    batch_results.append(result)
                    continue
                
                # Step 3: Check spam score (only for working, non-blacklisted)
                spam_score = await self.check_spam_score(ip)
                result.spam_score = spam_score
                
            except Exception as e:
                print(f"Error processing {proxy}: {e}")
            
            batch_results.append(result)
        
        return batch_results

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
        
        # Process in batches
        all_results = []
        BATCH_SIZE = 200
        
        for i in range(0, total_proxies, BATCH_SIZE):
            batch = proxies_list[i:i + BATCH_SIZE]
            batch_results = await self.process_proxy_batch(batch)
            all_results.extend(batch_results)
            
            # Progress update
            processed = min(i + BATCH_SIZE, total_proxies)
            elapsed = time.time() - start_time
            speed = processed / elapsed if elapsed > 0 else 0
            
            # Count stats
            working = sum(1 for r in all_results if r.is_working)
            clean = sum(1 for r in all_results if r.is_working and not r.is_blacklisted and r.spam_score <= 50)
            
            print(f"📊 Processed: {processed}/{total_proxies} | "
                  f"Working: {working} | Clean: {clean} | "
                  f"Speed: {speed:.1f} proxies/sec")
        
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
                result.response_time <= 3.0):
                final_proxies.append(result.proxy)
        
        return final_proxies

async def main():
    """Main function"""
    print("🚀 Starting Ultra Fast All-in-One Proxy Checker...")
    print("=" * 60)
    
    # Proxy sources
    proxy_sources = [
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/http.txt",
        "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
        "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
    ]
    
    checker = UltraFastProxyChecker()
    results = await checker.run_complete_check(proxy_sources)
    
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
    print(f"   Working Proxies: {working} ({working/total*100:.1f}%)")
    print(f"   Blacklisted: {blacklisted}")
    print(f"   Low Spam Score: {low_spam}")
    print(f"   ✅ Final Clean Proxies: {len(final_proxies)}")
    print("=" * 60)
    
    # Save results
    if final_proxies:
        with open("clean_proxies.txt", "w") as f:
            f.write("\n".join(final_proxies))
        print(f"💾 Results saved to clean_proxies.txt")
        
        # Also save detailed results
        with open("detailed_results.txt", "w") as f:
            f.write("Proxy,Working,ResponseTime,Blacklisted,SpamScore\n")
            for result in results:
                f.write(f"{result.proxy},{result.is_working},{result.response_time:.3f},"
                       f"{result.is_blacklisted},{result.spam_score}\n")
        print(f"📋 Detailed results saved to detailed_results.txt")
    else:
        print("❌ No clean proxies found")
    
    print("✅ Proxy check completed!")

if __name__ == "__main__":
    asyncio.run(main())
