#!/usr/bin/env python3
"""
Helper script to verify and debug GitHub Actions schedule
"""

import pytz
from datetime import datetime
import os

def check_schedule():
    """Check if the current time matches the scheduled times"""
    
    # Get current UTC time
    utc_now = datetime.now(pytz.UTC)
    current_hour = utc_now.hour
    current_minute = utc_now.minute
    
    print(f"Current UTC time: {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Current hour: {current_hour}, minute: {current_minute}")
    
    # Scheduled times (UTC)
    scheduled_times = [7, 19]  # 7 AM and 7 PM UTC
    
    if current_hour in scheduled_times and current_minute == 0:
        print("✅ Scheduled run time detected!")
        return True
    else:
        print("❌ Not scheduled run time")
        print(f"Next scheduled runs at: {', '.join(f'{h:02d}:00 UTC' for h in scheduled_times)}")
        return False

def simulate_schedule():
    """Simulate the cron schedule for testing"""
    print("🔍 Simulating GitHub Actions schedule...")
    print("Cron: '0 7 * * *' - Runs at 7 AM UTC daily")
    print("Cron: '0 19 * * *' - Runs at 7 PM UTC daily")
    print()
    
    # Test different times
    test_times = [
        "2024-01-15 07:00:00",
        "2024-01-15 19:00:00", 
        "2024-01-15 12:00:00",
        "2024-01-15 07:01:00"
    ]
    
    for time_str in test_times:
        test_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        test_time = pytz.UTC.localize(test_time)
        hour = test_time.hour
        minute = test_time.minute
        
        will_run = (hour in [7, 19] and minute == 0)
        status = "✅ WILL RUN" if will_run else "❌ WILL NOT RUN"
        
        print(f"{time_str} UTC - {status}")

if __name__ == "__main__":
    print("🕐 GitHub Actions Schedule Checker")
    print("=" * 40)
    
    check_schedule()
    print()
    simulate_schedule()
    
    # Check if running in GitHub Actions
    if os.getenv('GITHUB_ACTIONS') == 'true':
        print("\n🏃 Running in GitHub Actions environment")
    else:
        print("\n💻 Running locally")
