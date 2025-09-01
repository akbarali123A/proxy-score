import asyncio
import aiohttp
import socket
import re
import time
import subprocess
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import List, Set, Dict
import os
import resource

class UltraFastProxyChecker:
    def __init__(self):
        self.proxy_sources = [
            "https://raw.githubusercontent.com/akbarali123A/proxy_scraper/refs/heads/main/http_proxies.txt",
            "https://raw.githubusercontent.com/akbarali123A/proxy_scraper/refs/heads/main/https_proxies.txt", 
            "https://raw.githubusercontent.com/akbarali123A/proxy_scraper/refs/heads/main/socks4_proxies.txt",
            "https://raw.githubusercontent.com/akbarali123A/proxy_scraper/refs/heads/main/socks5_proxies.txt",
            
        ]
        self.clean_proxies = set()
        self.session = None

    def increase_limits(self):
        """Increase system limits without root permissions"""
        try:
            # Increase file descriptor limit
            resource.setrlimit(resource.RLIMIT_NOFILE, (8192, 8192))
        except:
            pass  # Ignore if we can't increase limits

    async def setup_session(self):
        """Setup optimized aiohttp session"""
        connector = aiohttp.TCPConnector(limit=1000, limit_per_host=100, use_dns_cache=True, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=5, connect=1, sock_connect=1, sock_read=1)
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
        """Fetch proxies from all sources quickly"""
        all_proxies = set()
        
        for url in self.proxy_sources:
            try:
                async with self.session.get(url, timeout=3) as response:
                    if response.status == 200:
                        text = await response.text()
                        lines = text.splitlines()
                        for line in lines[:10000]:  # Limit per source
                            line = line.strip()
                            if self.validate_proxy_format(line):
                                all_proxies.add(line)
            except:
                continue
                
        return all_proxies

    def mass_socket_check(self, proxies: List[str]) -> List[str]:
        """Mass socket connectivity check using multiprocessing"""
        print("🔌 Starting mass socket connectivity check...")
        
        # Split proxies into chunks for parallel processing
        chunk_size = 5000
        chunks = [proxies[i:i + chunk_size] for i in range(0, len(proxies), chunk_size)]
        
        working_proxies = []
        completed = 0
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            # Process chunks in parallel
            futures = {executor.submit(self.process_socket_chunk, chunk): chunk for chunk in chunks}
            
            for future in as_completed(futures):
                try:
                    chunk_result = future.result()
                    working_proxies.extend(chunk_result)
                    completed += len(chunk)
                    print(f"✅ Processed {completed:,}/{len(proxies):,} - {len(chunk_result)} working")
                except Exception as e:
                    print(f"❌ Chunk processing error: {e}")
        
        return working_proxies

    def process_socket_chunk(self, chunk: List[str]) -> List[str]:
        """Process a chunk of proxies with socket checks"""
        working = []
        
        for proxy in chunk:
            if self.quick_socket_check(proxy):
                working.append(proxy)
                
        return working

    def quick_socket_check(self, proxy: str) -> bool:
        """Ultra fast socket connectivity check"""
        try:
            ip, port_str = proxy.split(':', 1)
            port = int(port_str)
            
            # Create socket with very short timeout
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)  # 500ms timeout
            
            result = sock.connect_ex((ip, port))
            sock.close()
            
            return result == 0
            
        except:
            return False

    def mass_blacklist_check(self, proxies: List[str]) -> Set[str]:
        """Mass blacklist check using multiprocessing"""
        print("🛡️ Starting mass blacklist check...")
        
        # Extract unique IPs
        ip_proxy_map = {}
        unique_ips = set()
        
        for proxy in proxies:
            ip = proxy.split(':', 1)[0]
            unique_ips.add(ip)
            ip_proxy_map[ip] = proxy
        
        # Split IPs into chunks
        chunk_size = 2000
        ip_list = list(unique_ips)
        chunks = [ip_list[i:i + chunk_size] for i in range(0, len(ip_list), chunk_size)]
        
        blacklisted_ips = set()
        completed = 0
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            # Process chunks in parallel
            futures = {executor.submit(self.process_blacklist_chunk, chunk): chunk for chunk in chunks}
            
            for future in as_completed(futures):
                try:
                    chunk_result = future.result()
                    blacklisted_ips.update(chunk_result)
                    completed += len(chunk)
                    print(f"✅ Checked {completed:,}/{len(ip_list):,} IPs - {len(chunk_result)} blacklisted")
                except Exception as e:
                    print(f"❌ Blacklist chunk error: {e}")
        
        return blacklisted_ips

    def process_blacklist_chunk(self, chunk: List[str]) -> Set[str]:
        """Process a chunk of IPs for blacklist checking"""
        blacklisted = set()
        
        for ip in chunk:
            if self.check_single_blacklist(ip):
                blacklisted.add(ip)
                
        return blacklisted

    def check_single_blacklist(self, ip: str) -> bool:
        """Check single IP against blacklist using Python DNS"""
        try:
            reversed_ip = ".".join(ip.split(".")[::-1])
            query = f"{reversed_ip}.zen.spamhaus.org"
            
            # Use Python's socket for DNS lookup (no subprocess)
            try:
                socket.gethostbyname(query)
                return True  # If resolved, it's blacklisted
            except socket.gaierror:
                return False  # Not blacklisted
                
        except:
            return False

    async def run(self):
        """Main method optimized for 5 lakh+ proxies"""
        print("🚀 Starting Ultra Fast Mass Proxy Checker...")
        print("=" * 60)
        start_time = time.time()
        
        self.increase_limits()
        await self.setup_session()
        
        # Step 1: Fetch all proxies
        print("📥 Fetching proxies from sources...")
        all_proxies = await self.fetch_proxies()
        print(f"✅ Found {len(all_proxies):,} unique proxies")
        
        if not all_proxies:
            print("❌ No proxies found!")
            return set()
        
        proxies_list = list(all_proxies)
        total_proxies = len(proxies_list)
        
        # Step 2: Mass socket check
        working_proxies = self.mass_socket_check(proxies_list)
        print(f"✅ {len(working_proxies):,} proxies are working")
        
        if not working_proxies:
            return set()
        
        # Step 3: Mass blacklist check
        blacklisted_ips = self.mass_blacklist_check(working_proxies)
        print(f"🚫 {len(blacklisted_ips):,} IPs are blacklisted")
        
        # Step 4: Filter final results
        for proxy in working_proxies:
            ip = proxy.split(':', 1)[0]
            if ip not in blacklisted_ips:
                self.clean_proxies.add(proxy)
        
        # Close session
        await self.session.close()
        
        total_time = time.time() - start_time
        print("=" * 60)
        print(f"🎉 Completed in {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
        print(f"✅ Final clean proxies: {len(self.clean_proxies):,}")
        print(f"⚡ Speed: {total_proxies/total_time:.0f} proxies/second")
        print("=" * 60)
        
        return self.clean_proxies

def main():
    """Main function with robust error handling"""
    try:
        checker = UltraFastProxyChecker()
        
        # Run the checker
        clean_proxies = asyncio.run(checker.run())
        
        # Save results
        if clean_proxies:
            with open("clean_proxies.txt", "w") as f:
                f.write("\n".join(clean_proxies))
            print(f"💾 Saved {len(clean_proxies):,} clean proxies to clean_proxies.txt")
        else:
            print("❌ No clean proxies found")
            with open("clean_proxies.txt", "w") as f:
                f.write("")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        with open("clean_proxies.txt", "w") as f:
            f.write("")
    finally:
        print("✅ Process completed!")

if __name__ == "__main__":
    main()
