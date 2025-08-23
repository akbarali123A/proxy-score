import asyncio
import aiohttp
import socket
import re
import time
import random
from typing import List, Set, Dict
from concurrent.futures import ThreadPoolExecutor
import os

class UltraFastProxyChecker:
    def __init__(self):
        self.dns_servers = ['1.1.1.1', '8.8.8.8', '9.9.9.9']
        self.session = None
        self.proxy_sources = [
            "https://raw.githubusercontent.com/akbarali123A/proxy_scraper/refs/heads/main/http_proxies.txt",
            "https://raw.githubusercontent.com/akbarali123A/proxy_scraper/refs/heads/main/https_proxies.txt",
            "https://raw.githubusercontent.com/akbarali123A/proxy_scraper/refs/heads/main/socks4_proxies.txt",
            "https://raw.githubusercontent.com/akbarali123A/proxy_scraper/refs/heads/main/socks5_proxies.txt",
            
        ]
        self.checked_ips = set()
        self.clean_proxies = set()

    async def setup_session(self):
        """Setup aiohttp session with connection pooling"""
        connector = aiohttp.TCPConnector(limit=1000, limit_per_host=100, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=30, connect=2, sock_connect=2, sock_read=2)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)

    def validate_proxy_format(self, proxy: str) -> bool:
        """Ultra fast proxy format validation"""
        if not proxy or ':' not in proxy:
            return False
            
        try:
            ip, port = proxy.split(':', 1)
            # Fast IP validation with regex
            if not re.match(r'^\d{1,3}(\.\d{1,3}){3}$', ip):
                return False
            # Fast port validation
            port_num = int(port)
            return 1 <= port_num <= 65535
        except:
            return False

    async def fetch_proxies_batch(self, urls: List[str]) -> Set[str]:
        """Fetch proxies from multiple sources concurrently"""
        tasks = []
        for url in urls:
            task = asyncio.create_task(self.fetch_single_source(url))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_proxies = set()
        for result in results:
            if isinstance(result, set):
                all_proxies.update(result)
        
        return all_proxies

    async def fetch_single_source(self, url: str) -> Set[str]:
        """Fetch proxies from a single source"""
        try:
            async with self.session.get(url, timeout=5) as response:
                if response.status == 200:
                    text = await response.text()
                    proxies = set()
                    for line in text.splitlines():
                        line = line.strip()
                        if self.validate_proxy_format(line):
                            proxies.add(line)
                    print(f"✅ Fetched {len(proxies)} from {url.split('/')[-1]}")
                    return proxies
        except Exception as e:
            print(f"❌ Failed {url}: {str(e)}")
        return set()

    async def check_proxy_connectivity(self, proxy: str) -> bool:
        """Ultra fast connectivity check using socket"""
        try:
            ip, port = proxy.split(':', 1)
            port = int(port)
            
            # Socket connection check (fastest method)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, port))
            sock.close()
            
            return result == 0
        except:
            return False

    def is_ip_checked(self, ip: str) -> bool:
        """Check if IP was already processed"""
        return ip in self.checked_ips

    async def check_ip_blacklisted(self, ip: str) -> bool:
        """Fast DNS blacklist check using system dig command"""
        try:
            # Use system's dig command for faster DNS lookup
            blacklists = ["zen.spamhaus.org", "bl.spamcop.net"]
            
            for blacklist in blacklists:
                try:
                    # Reverse IP for DNSBL query
                    reversed_ip = ".".join(ip.split(".")[::-1])
                    query = f"{reversed_ip}.{blacklist}"
                    
                    # Use subprocess for parallel DNS checks
                    process = await asyncio.create_subprocess_exec(
                        'dig', '+short', '+time=1', '+tries=1', query,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, _ = await process.communicate()
                    
                    if stdout and not b"NXDOMAIN" in stdout:
                        return True
                except:
                    continue
                    
            return False
        except:
            return False

    async def process_proxy_batch(self, batch: List[str]) -> Set[str]:
        """Process a batch of proxies concurrently"""
        batch_clean = set()
        
        # First pass: Quick socket connectivity check
        connectivity_tasks = []
        for proxy in batch:
            connectivity_tasks.append(self.check_proxy_connectivity(proxy))
        
        connectivity_results = await asyncio.gather(*connectivity_tasks)
        
        # Second pass: Detailed checks for working proxies
        detailed_tasks = []
        working_proxies = []
        
        for proxy, is_working in zip(batch, connectivity_results):
            if is_working:
                ip = proxy.split(':', 1)[0]
                if not self.is_ip_checked(ip):
                    self.checked_ips.add(ip)
                    working_proxies.append(proxy)
                    detailed_tasks.append(self.check_ip_blacklisted(ip))
        
        # Process blacklist checks in parallel
        if detailed_tasks:
            blacklist_results = await asyncio.gather(*detailed_tasks)
            
            # Final filtering
            for proxy, is_blacklisted in zip(working_proxies, blacklist_results):
                if not is_blacklisted:
                    batch_clean.add(proxy)
        
        return batch_clean

    async def run_mass_check(self):
        """Main method to check 5 lakh+ proxies"""
        print("🚀 Starting Ultra Fast Mass Proxy Checker...")
        print("=" * 60)
        start_time = time.time()
        
        await self.setup_session()
        
        # Step 1: Fetch all proxies
        print("📥 Fetching proxies from all sources...")
        all_proxies = await self.fetch_proxies_batch(self.proxy_sources)
        print(f"✅ Total unique proxies found: {len(all_proxies):,}")
        
        if not all_proxies:
            print("❌ No proxies found!")
            return set()
        
        # Convert to list for processing
        proxies_list = list(all_proxies)
        total_proxies = len(proxies_list)
        print(f"🔧 Starting processing of {total_proxies:,} proxies...")
        
        # Process in optimized batches
        BATCH_SIZE = 5000  # Large batches for efficiency
        processed = 0
        
        for i in range(0, total_proxies, BATCH_SIZE):
            batch = proxies_list[i:i + BATCH_SIZE]
            batch_clean = await self.process_proxy_batch(batch)
            self.clean_proxies.update(batch_clean)
            
            processed += len(batch)
            elapsed = time.time() - start_time
            speed = processed / elapsed if elapsed > 0 else 0
            
            print(f"📊 Processed: {processed:,}/{total_proxies:,} | "
                  f"Clean: {len(self.clean_proxies):,} | "
                  f"Speed: {speed:,.0f} proxies/sec")
            
            # Clear memory periodically
            if i % 20000 == 0:
                await asyncio.sleep(0.1)
        
        # Close session
        await self.session.close()
        
        total_time = time.time() - start_time
        print("=" * 60)
        print(f"🎉 Completed in {total_time:.2f} seconds")
        print(f"✅ Final clean proxies: {len(self.clean_proxies):,}")
        print("=" * 60)
        
        return self.clean_proxies

async def main():
    """Main function with timeout handling"""
    try:
        checker = UltraFastProxyChecker()
        
        # Run with timeout to prevent GitHub cancellation
        clean_proxies = await asyncio.wait_for(
            checker.run_mass_check(),
            timeout=7200  # 120 minutes timeout
        )
        
        # Save results
        if clean_proxies:
            with open("clean_proxies.txt", "w") as f:
                f.write("\n".join(clean_proxies))
            print(f"💾 Saved {len(clean_proxies):,} clean proxies to clean_proxies.txt")
        else:
            print("❌ No clean proxies found")
            # Create empty file
            with open("clean_proxies.txt", "w") as f:
                f.write("")
                
    except asyncio.TimeoutError:
        print("⏰ Timeout reached! Saving collected results...")
        # Save whatever we have so far
        if hasattr(checker, 'clean_proxies') and checker.clean_proxies:
            with open("clean_proxies.txt", "w") as f:
                f.write("\n".join(checker.clean_proxies))
            print(f"💾 Saved {len(checker.clean_proxies):,} proxies (partial results)")
        else:
            with open("clean_proxies.txt", "w") as f:
                f.write("")
    except Exception as e:
        print(f"❌ Error: {e}")
        # Ensure file exists even on error
        with open("clean_proxies.txt", "w") as f:
            f.write("")
    finally:
        print("✅ Proxy check completed!")

if __name__ == "__main__":
    asyncio.run(main())
