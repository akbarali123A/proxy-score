import asyncio
import aiodns
import socket
from typing import List, Dict
import time

class UltraFastBlacklistChecker:
    def __init__(self):
        self.dns_servers = [
            '1.1.1.1',  # Cloudflare
            '8.8.8.8',  # Google
            '9.9.9.9',  # Quad9
        ]
        self.resolver = None
        self.blacklist_domains = [
            "zen.spamhaus.org",
            "bl.spamcop.net",
            "dnsbl.sorbs.net",
            "xbl.spamhaus.org",
            "pbl.spamhaus.org",
            "dnsbl-1.uceprotect.net",
            "b.barracudacentral.org",
        ]
        
    async def setup_resolver(self):
        """Setup async DNS resolver"""
        self.resolver = aiodns.DNSResolver()
        self.resolver.nameservers = self.dns_servers
        
    async def check_single_blacklist(self, query: str, domain: str) -> bool:
        """Check a single blacklist asynchronously"""
        try:
            full_query = f"{query}.{domain}"
            await self.resolver.query(full_query, 'A')
            return True  # If resolved, IP is blacklisted
        except aiodns.error.DNSError:
            return False  # Not listed in this blacklist
        except Exception:
            return False
            
    async def is_ip_blacklisted(self, ip: str) -> bool:
        """Check if IP is blacklisted using async DNS queries"""
        if not self.resolver:
            await self.setup_resolver()
            
        # Reverse the IP for DNSBL query
        reversed_ip = ".".join(ip.split(".")[::-1])
        
        # Create tasks for all blacklist checks
        tasks = []
        for domain in self.blacklist_domains:
            tasks.append(self.check_single_blacklist(reversed_ip, domain))
        
        # Run all checks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Return True if any blacklist returned positive
        return any(results)
    
    async def check_multiple_ips(self, ips: List[str]) -> Dict[str, bool]:
        """Check multiple IPs asynchronously with maximum concurrency"""
        if not self.resolver:
            await self.setup_resolver()
            
        results = {}
        tasks = {ip: self.is_ip_blacklisted(ip) for ip in ips}
        
        # Run all IP checks concurrently
        completed = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        # Map results back to IPs
        for ip, result in zip(tasks.keys(), completed):
            if isinstance(result, Exception):
                results[ip] = False
            else:
                results[ip] = result
                
        return results

# Quick test
if __name__ == "__main__":
    async def test_checker():
        checker = UltraFastBlacklistChecker()
        test_ips = ["8.8.8.8", "1.1.1.1", "127.0.0.2"]
        
        start = time.time()
        results = await checker.check_multiple_ips(test_ips)
        end = time.time()
        
        for ip, blacklisted in results.items():
            print(f"{ip}: {'BLACKLISTED' if blacklisted else 'CLEAN'}")
        
        print(f"Checked {len(test_ips)} IPs in {end-start:.3f} seconds")
    
    asyncio.run(test_checker())
