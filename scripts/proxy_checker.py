import asyncio
import aiohttp
import socket
import re
import time
import random
import subprocess
from typing import List, Set
import os

class UltraFastProxyChecker:
    def __init__(self):
        self.proxy_sources = [
            "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt", 
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/http.txt",
            "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
            "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/http.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
        ]
        self.checked_ips = set()
        self.clean_proxies = set()
        self.session = None

    async def setup_session(self):
        """Setup optimized aiohttp session"""
        connector = aiohttp.TCPConnector(limit=5000, limit_per_host=1000, use_dns_cache=True)
        timeout = aiohttp.ClientTimeout(total=10, connect=1, sock_connect=1, sock_read=1)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)

    def validate_proxy_format(self, proxy: str) -> bool:
        """Ultra fast proxy format validation"""
        if not proxy or len(proxy) > 21 or ':' not in proxy:
            return False
            
        try:
            ip, port_str = proxy.split(':', 1)
            # Fast IP validation
            if not re.match(r'^\d{1,3}(\.\d{1,3}){3}$', ip):
                return False
            # Fast port validation
            port = int(port_str)
            return 1 <= port <= 65535
        except:
            return False

    async def fetch_proxies(self) -> Set[str]:
        """Fetch proxies from all sources with aggressive timeout"""
        all_proxies = set()
        fetch_tasks = []
        
        for url in self.proxy_sources:
            task = asyncio.create_task(self.fetch_single_source(url))
            fetch_tasks.append(task)
        
        # Wait for all with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*fetch_tasks, return_exceptions=True),
                timeout=300  # 5 minutes max for fetching
            )
            
            for result in results:
                if isinstance(result, set):
                    all_proxies.update(result)
                    
        except asyncio.TimeoutError:
            print("⚠️  Fetch timeout, using collected proxies")
        
        return all_proxies

    async def fetch_single_source(self, url: str) -> Set[str]:
        """Fetch from single source with quick timeout"""
        try:
            async with self.session.get(url, timeout=3) as response:
                if response.status == 200:
                    text = await response.text()
                    proxies = set()
                    lines = text.splitlines()
                    for line in lines[:10000]:  # Limit per source
                        line = line.strip()
                        if self.validate_proxy_format(line):
                            proxies.add(line)
                    return proxies
        except:
            return set()

    def bulk_connectivity_check(self, proxies: List[str]) -> List[str]:
        """Mass socket connectivity check using thread pool"""
        working_proxies = []
        
        with ThreadPoolExecutor(max_workers=1000) as executor:
            results = executor.map(self.quick_socket_check, proxies)
            
            for proxy, is_working in zip(proxies, results):
                if is_working:
                    working_proxies.append(proxy)
        
        return working_proxies

    def quick_socket_check(self, proxy: str) -> bool:
        """Ultra fast socket connectivity check"""
        try:
            ip, port_str = proxy.split(':', 1)
            port = int(port_str)
            
            # Create socket with very short timeout
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)  # 500ms timeout
            
            # Non-blocking connect
            sock.setblocking(False)
            try:
                sock.connect((ip, port))
                # Wait for connection with very short timeout
                ready = socket.select([sock], [], [], 0.5)
                if ready[0]:
                    sock.close()
                    return True
            except (BlockingIOError, OSError):
                pass
                
            sock.close()
            return False
            
        except:
            return False

    def bulk_blacklist_check(self, ips: List[str]) -> Set[str]:
        """Mass blacklist check using system dig command"""
        blacklisted_ips = set()
        batch_size = 500
        
        for i in range(0, len(ips), batch_size):
            batch = ips[i:i + batch_size]
            blacklisted_batch = self.check_blacklist_batch(batch)
            blacklisted_ips.update(blacklisted_batch)
        
        return blacklisted_ips

    def check_blacklist_batch(self, ips: List[str]) -> Set[str]:
        """Check batch of IPs against blacklists"""
        blacklisted = set()
        
        # Use zen.spamhaus.org only (most reliable)
        for ip in ips:
            if self.is_blacklisted(ip):
                blacklisted.add(ip)
        
        return blacklisted

    def is_blacklisted(self, ip: str) -> bool:
        """Check single IP against blacklist using dig"""
        try:
            reversed_ip = ".".join(ip.split(".")[::-1])
            query = f"{reversed_ip}.zen.spamhaus.org"
            
            result = subprocess.run(
                ['dig', '+short', '+time=1', '+tries=1', query],
                capture_output=True,
                text=True,
                timeout=1
            )
            
            return bool(result.stdout.strip())
        except:
            return False

    async def run_mass_check(self):
        """Main method optimized for 5 lakh+ proxies"""
        print("🚀 Starting Ultra Fast Mass Proxy Checker...")
        print("=" * 60)
        start_time = time.time()
        
        await self.setup_session()
        
        # Step 1: Fetch all proxies quickly
        print("📥 Fetching proxies from sources...")
        all_proxies = await self.fetch_proxies()
        print(f"✅ Found {len(all_proxies):,} unique proxies")
        
        if not all_proxies:
            print("❌ No proxies found!")
            return set()
        
        # Convert to list for processing
        proxies_list = list(all_proxies)
        total_proxies = len(proxies_list)
        print(f"🔧 Starting mass processing of {total_proxies:,} proxies...")
        
        # Step 2: Bulk connectivity check (fastest method)
        print("🔌 Checking connectivity...")
        working_proxies = self.bulk_connectivity_check(proxies_list)
        print(f"✅ {len(working_proxies):,} proxies are working")
        
        # Step 3: Extract IPs for blacklist check
        working_ips = []
        proxy_ip_map = {}
        
        for proxy in working_proxies:
            ip = proxy.split(':', 1)[0]
            working_ips.append(ip)
            proxy_ip_map[ip] = proxy
        
        # Step 4: Bulk blacklist check
        print("🛡️  Checking blacklists...")
        blacklisted_ips = self.bulk_blacklist_check(working_ips)
        print(f"🚫 {len(blacklisted_ips):,} IPs are blacklisted")
        
        # Step 5: Filter final results
        for ip in working_ips:
            if ip not in blacklisted_ips:
                self.clean_proxies.add(proxy_ip_map[ip])
        
        # Close session
        await self.session.close()
        
        total_time = time.time() - start_time
        print("=" * 60)
        print(f"🎉 Completed in {total_time:.2f} seconds")
        print(f"✅ Final clean proxies: {len(self.clean_proxies):,}")
        print(f"⚡ Speed: {total_proxies/total_time:.0f} proxies/second")
        print("=" * 60)
        
        return self.clean_proxies

async def main():
    """Main function with robust error handling"""
    try:
        checker = UltraFastProxyChecker()
        
        # Run with extended timeout
        clean_proxies = await asyncio.wait_for(
            checker.run_mass_check(),
            timeout=3600  # 1 hour timeout
        )
        
        # Save results
        if clean_proxies:
            with open("clean_proxies.txt", "w") as f:
                f.write("\n".join(clean_proxies))
            print(f"💾 Saved {len(clean_proxies):,} clean proxies")
        else:
            print("❌ No clean proxies found")
            with open("clean_proxies.txt", "w") as f:
                f.write("")
                
    except asyncio.TimeoutError:
        print("⏰ 1-hour timeout reached! Saving collected results...")
        if hasattr(checker, 'clean_proxies') and checker.clean_proxies:
            with open("clean_proxies.txt", "w") as f:
                f.write("\n".join(checker.clean_proxies))
            print(f"💾 Saved {len(checker.clean_proxies):,} proxies (partial)")
        else:
            with open("clean_proxies.txt", "w") as f:
                f.write("")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        with open("clean_proxies.txt", "w") as f:
            f.write("")
    finally:
        print("✅ Process completed!")

if __name__ == "__main__":
    # Increase resource limits
    import resource
    resource.setrlimit(resource.RLIMIT_NOFILE, (100000, 100000))
    
    asyncio.run(main())
