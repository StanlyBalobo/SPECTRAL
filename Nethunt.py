#!/usr/bin/env python3
"""
Universal WiFi Monitor — Kali Linux & Termux (Android)
======================================================
Flow:
  1. Detect platform (Kali Linux or Termux)
  2. Enable WiFi / scan available networks
  3. List saved networks
  4. Let you pick one (number, name, or saved)
  5. Auto-connect using platform-specific method
  6. Start monitoring traffic

Requirements:
  Kali:  sudo apt install python3-scapy wireless-tools iw nmcli
  Termux: pkg install python termux-api root-repo && pip install scapy colorama

Authorized use only. Ensure proper scope.
"""

import argparse
import json
import os
import platform
import re
import socket
import struct
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime

# ─────────────────────────────────────────────────────
#  PLATFORM DETECTION
# ─────────────────────────────────────────────────────

def detect_platform():
    """
    Returns 'termux', 'kali', or 'linux'.
    Checks environment variables and files unique to each.
    """
    # Termux check: TERMUX_VERSION env var, or /data/data/com.termux exists
    if os.environ.get('TERMUX_VERSION'):
        return 'termux'
    if os.path.exists('/data/data/com.termux'):
        return 'termux'

    # Kali check
    try:
        with open('/etc/os-release') as f:
            content = f.read()
            if 'kali' in content.lower():
                return 'kali'
    except (FileNotFoundError, IOError):
        pass

    # Generic Linux
    if sys.platform.startswith('linux'):
        return 'linux'

    return sys.platform


PLATFORM = detect_platform()

# ─────────────────────────────────────────────────────
#  COLOR
# ─────────────────────────────────────────────────────

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    HAVE_COLORAMA = True
except ImportError:
    HAVE_COLORAMA = False
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ''
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ''

try:
    from scapy.all import sniff, IP, TCP, UDP, DNS, DNSQR, Raw
    HAVE_SCAPY = True
except ImportError:
    HAVE_SCAPY = False


# ─────────────────────────────────────────────────────
#  UTILITIES
# ─────────────────────────────────────────────────────

def cprint(color, tag, msg):
    ts = datetime.now().strftime('%H:%M:%S')
    if HAVE_COLORAMA:
        print(f"{Fore.WHITE}[{ts}]{Style.RESET_ALL} {color}[{tag}]{Style.RESET_ALL} {msg}")
    else:
        print(f"[{ts}] [{tag}] {msg}")


def run_cmd(cmd, timeout=15, shell=False):
    """Run a shell command and return (stdout, stderr, returncode)."""
    try:
        r = subprocess.run(
            cmd if not shell else cmd,
            capture_output=True, text=True, timeout=timeout,
            shell=shell
        )
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return '', 'Timeout', -1
    except FileNotFoundError as e:
        return '', f'Command not found: {e}', -1
    except PermissionError:
        return '', 'Permission denied', -1


def require_root():
    """Check if running as root (needed for monitor mode / raw sockets)."""
    if os.geteuid() != 0:
        cprint(Fore.RED, 'ROOT', 'This needs root privileges.')
        cprint(Fore.YELLOW, 'HINT', f'Run with: sudo python3 {os.path.basename(sys.argv[0])}')
        if PLATFORM == 'termux':
            cprint(Fore.YELLOW, 'HINT', 'Run with: tsu python3 ...')
        sys.exit(1)


# ─────────────────────────────────────────────────────
#  DEPENDENCY CHECK (platform-specific)
# ─────────────────────────────────────────────────────

def check_dependencies():
    """Check required tools based on platform."""
    missing = []

    if PLATFORM == 'termux':
        for tool in ['termux-wifi-scaninfo', 'termux-wifi-connectioninfo', 'termux-wifi-enable']:
            if subprocess.run(['which', tool], capture_output=True).returncode != 0:
                missing.append(tool)
        if missing:
            cprint(Fore.RED, 'MISSING', 'Termux:API commands not found. Install:')
            cprint(Fore.YELLOW, 'INSTALL', 'pkg install termux-api')
            cprint(Fore.YELLOW, 'INSTALL', 'Also install Termux:API app from F-Droid')
            cprint(Fore.YELLOW, 'PERMS', 'Grant Location permission to Termux')
            sys.exit(1)
    else:
        # Kali / Linux checks
        checks = {
            'nmcli': 'network-manager',
            'iw': 'iw',
            'iwconfig': 'wireless-tools',
        }
        for tool, pkg in checks.items():
            if subprocess.run(['which', tool], capture_output=True).returncode != 0:
                missing.append(f'{tool} (apt install {pkg})')
        if missing:
            cprint(Fore.YELLOW, 'MISSING', 'Some tools not found:')
            for m in missing:
                print(f'  • {m}')
            cprint(Fore.YELLOW, 'NOTE', 'Continuing anyway (some features may be limited).')


# ─────────────────────────────────────────────────────
#  WIFI: ENABLE / LIST INTERFACES
# ─────────────────────────────────────────────────────

def get_wifi_interface():
    """Detect the wireless interface name."""
    if PLATFORM == 'termux':
        return 'wlan0'

    # Kali/Linux: list wireless interfaces
    out, _, rc = run_cmd(['iwconfig'], timeout=5)
    if rc != 0:
        out, _, _ = run_cmd(['iw', 'dev'], timeout=5)

    if out:
        # Look for wlan0, wlp*, etc.
        for word in out.split():
            word = word.strip(':')
            if re.match(r'^wlan\d+$', word) or re.match(r'^wlp\d+s\d+', word) or re.match(r'^wlx', word):
                return word
            if word.startswith('wlan') or word.startswith('wlp'):
                return word

    # Fallback
    return 'wlan0'


def wifi_enable_kali():
    """Ensure WiFi radio is on (Kali/Linux)."""
    # Try rfkill
    run_cmd(['rfkill', 'unblock', 'wifi'], timeout=5)
    # Try nmcli
    run_cmd(['nmcli', 'radio', 'wifi', 'on'], timeout=5)
    # Try ifconfig/ip
    iface = get_wifi_interface()
    run_cmd(['ip', 'link', 'set', iface, 'up'], timeout=5)
    time.sleep(1)


def wifi_enable():
    """Enable WiFi (platform-agnostic)."""
    if PLATFORM == 'termux':
        out, err, rc = run_cmd(['termux-wifi-enable', 'true'])
        if rc != 0:
            cprint(Fore.RED, 'WIFI', f'Failed to enable WiFi: {err}')
            return False
        time.sleep(1)
        return True
    else:
        wifi_enable_kali()
        return True


# ─────────────────────────────────────────────────────
#  SCAN: AVAILABLE NETWORKS
# ─────────────────────────────────────────────────────

def scan_networks():
    """
    Platform-agnostic WiFi scan.
    Returns list of dicts: {ssid, bssid, security, frequency, rssi, channel}
    """
    if PLATFORM == 'termux':
        return _scan_termux()
    else:
        return _scan_kali()


def _scan_termux():
    """Scan via termux-wifi-scaninfo (passive, reads Android's last scan)."""
    out, err, rc = run_cmd(['termux-wifi-scaninfo'])
    if rc != 0 or not out:
        cprint(Fore.YELLOW, 'SCAN', 'No scan data. Trying iwlist fallback...')
        out, err, rc = run_cmd(['iwlist', 'wlan0', 'scan'], timeout=20)
        if rc != 0 or not out:
            cprint(Fore.RED, 'SCAN', f'Scan failed: {err}')
            return []
        return _parse_iwlist(out)

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []

    networks = []
    for ap in data if isinstance(data, list) else [data]:
        ssid = ap.get('ssid', '').strip()
        if not ssid:
            continue
        caps = ap.get('capabilities', '')
        freq = ap.get('frequency', 0) or ap.get('center_frequency', 0)
        networks.append({
            'ssid': ssid,
            'bssid': ap.get('bssid', ''),
            'security': _detect_security(caps),
            'frequency': freq,
            'rssi': ap.get('rssi', 0) or ap.get('level', 0),
            'channel': _freq_to_channel(freq) if freq else '?',
            'capabilities': caps,
        })
    return networks


def _scan_kali():
    """Scan via nmcli or iwlist (Kali/Linux)."""
    # Method 1: nmcli (best)
    out, _, rc = run_cmd(['nmcli', '-f', 'SSID,BSSID,SECURITY,FREQ,SIGNAL,CHAN', '-t',
                          'device', 'wifi', 'list', '--rescan', 'yes'], timeout=30)
    if rc == 0 and out:
        networks = []
        for line in out.split('\n'):
            if not line.strip():
                continue
            parts = line.split(':')
            if len(parts) >= 6:
                ssid = parts[0].strip()
                if not ssid:
                    continue
                networks.append({
                    'ssid': ssid,
                    'bssid': parts[1].strip(),
                    'security': _simplify_security(parts[2].strip()),
                    'frequency': _channel_to_freq(int(parts[5])) if parts[5].isdigit() else 0,
                    'rssi': int(parts[4]) if parts[4].isdigit() else 0,
                    'channel': parts[5] if parts[5].isdigit() else '?',
                })
        if networks:
            return networks

    # Method 2: iwlist
    iface = get_wifi_interface()
    out, _, rc = run_cmd(['iwlist', iface, 'scan'], timeout=30)
    if rc == 0 and out:
        return _parse_iwlist(out)

    # Method 3: iw dev scan
    out, _, rc = run_cmd(['iw', 'dev', iface, 'scan'], timeout=30)
    if rc == 0 and out:
        return _parse_iw_output(out)

    cprint(Fore.RED, 'SCAN', 'All scan methods failed. Is WiFi enabled?')
    return []


def _parse_iwlist(iw_out):
    """Parse iwlist scan output."""
    networks = []
    current = {}
    for line in iw_out.split('\n'):
        line = line.strip()
        if 'ESSID:' in line:
            ssid = line.split('ESSID:"')[1].rstrip('"')
            if current.get('ssid'):
                networks.append(current)
            current = {'ssid': ssid, 'bssid': '', 'security': '?', 'rssi': 0, 'channel': '?', 'frequency': 0}
        elif 'Address:' in line:
            m = re.search(r'Address:\s*([0-9A-Fa-f:]+)', line)
            if m:
                current['bssid'] = m.group(1).upper()
        elif 'Frequency:' in line or 'Frequency' in line:
            m = re.search(r'Frequency:([\d.]+)\s*GHz', line)
            if m:
                freq = float(m.group(1)) * 1000
                current['frequency'] = freq
                current['channel'] = _freq_to_channel(freq)
            else:
                m2 = re.search(r'Channel\s*(\d+)', line)
                if m2:
                    current['channel'] = m2.group(1)
                    current['frequency'] = _channel_to_freq(int(m2.group(1)))
        elif 'Signal level' in line:
            m = re.search(r'Signal level[=:]\s*(-?\d+)', line)
            if m:
                current['rssi'] = int(m.group(1))
        elif 'Encryption' in line:
            current['security'] = 'open' if 'off' in line.lower() else 'wpa2'

    if current.get('ssid'):
        networks.append(current)
    return networks


def _parse_iw_output(iw_out):
    """Parse `iw dev scan` output."""
    networks = []
    current = {}
    for line in iw_out.split('\n'):
        line = line.strip()
        if 'SSID:' in line:
            ssid = line.split('SSID: ')[-1].strip()
            if current.get('ssid'):
                networks.append(current)
            current = {'ssid': ssid, 'bssid': '', 'security': '?', 'rssi': 0, 'channel': '?', 'frequency': 0}
        elif 'BSS' in line and re.search(r'BSS\s+([0-9a-f:]+)', line, re.I):
            m = re.search(r'BSS\s+([0-9a-f:]+)', line, re.I)
            if m and current.get('ssid'):
                current['bssid'] = m.group(1).upper()
        elif 'freq:' in line:
            m = re.search(r'freq:\s*(\d+)', line)
            if m:
                freq = int(m.group(1))
                current['frequency'] = freq
                current['channel'] = _freq_to_channel(freq)
        elif 'signal:' in line:
            m = re.search(r'signal:\s*(-?\d+)', line)
            if m:
                current['rssi'] = int(m.group(1))
    if current.get('ssid'):
        networks.append(current)
    return networks


def _detect_security(caps):
    caps_lower = caps.lower()
    if 'wpa3' in caps_lower or 'sae' in caps_lower:
        return 'wpa3'
    if 'wpa2' in caps_lower or 'rsn' in caps_lower:
        return 'wpa2'
    if 'wpa' in caps_lower:
        return 'wpa'
    if 'wep' in caps_lower:
        return 'wep'
    return 'open'


def _simplify_security(sec_str):
    s = sec_str.lower()
    if 'wpa3' in s:
        return 'wpa3'
    if 'wpa2' in s:
        return 'wpa2'
    if 'wpa' in s:
        return 'wpa'
    if 'wep' in s:
        return 'wep'
    if 'open' in s or not s or s == '--':
        return 'open'
    return sec_str


def _freq_to_channel(freq_mhz):
    freq = int(freq_mhz)
    if 2412 <= freq <= 2484:
        return (freq - 2412) // 5 + 1
    if 5170 <= freq <= 5825:
        return (freq - 5170) // 5 + 34
    return '?'


def _channel_to_freq(ch):
    ch = int(ch)
    if 1 <= ch <= 13:
        return 2412 + (ch - 1) * 5
    if ch == 14:
        return 2484
    if 34 <= ch <= 165:
        return 5170 + (ch - 34) * 5
    return 0


# ─────────────────────────────────────────────────────
#  SAVED NETWORKS
# ─────────────────────────────────────────────────────

def list_saved_networks():
    """List previously saved WiFi networks (platform-specific)."""
    if PLATFORM == 'termux':
        return _list_saved_termux()
    else:
        return _list_saved_kali()


def _list_saved_termux():
    """Use Android cmd wifi to list saved networks."""
    out, err, rc = run_cmd(['cmd', 'wifi', 'list-networks'], timeout=5)
    if rc != 0 or not out:
        return []

    saved = []
    lines = out.split('\n')
    for line in lines[1:]:  # Skip header
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            net_id = parts[0]
            ssid = parts[1].strip('"\'')
            sec = parts[2] if len(parts) >= 3 else '?'
            password = _try_get_saved_password_wpa_cli(net_id)
            saved.append({
                'id': net_id,
                'ssid': ssid,
                'security': sec,
                'password': password,
            })
    return saved


def _try_get_saved_password_wpa_cli(net_id):
    """Try to get saved password via wpa_cli (root only)."""
    try:
        out, _, rc = run_cmd([
            'wpa_cli', '-p', '/data/misc/wifi/sockets/', '-i', 'wlan0',
            'get_network', net_id, 'psk'
        ], timeout=5)
        if rc == 0 and out and out not in ('FAIL', 'psk'):
            return out.strip().strip('"')
    except Exception:
        pass
    return None


def _list_saved_kali():
    """List saved networks from NetworkManager (Kali/Linux)."""
    # Method 1: nmcli
    out, _, rc = run_cmd(
        ['nmcli', '-f', 'NAME,UUID,TYPE,DEVICE', '-t', 'connection', 'show'],
        timeout=10
    )
    if rc != 0 or not out:
        return []

    saved = []
    for line in out.split('\n'):
        if not line.strip():
            continue
        parts = line.split(':')
        if len(parts) >= 1:
            name = parts[0].strip()
            if name:
                # Try to get the actual SSID / password from the connection
                ssid_out, _, _ = run_cmd(
                    ['nmcli', '-t', '-f', '802-11-wireless.ssid', 'connection', 'show', name],
                    timeout=5
                )
                ssid = ssid_out.strip() if ssid_out else name

                pwd_out, _, _ = run_cmd(
                    ['nmcli', '-t', '-f', '802-11-wireless-security.psk', 'connection', 'show', name],
                    timeout=5
                )
                password = pwd_out.strip() if pwd_out and 'not' not in pwd_out.lower() else None

                sec_type = _get_connection_security(name)

                saved.append({
                    'id': name,
                    'ssid': ssid,
                    'security': sec_type,
                    'password': password,
                })

    return saved


def _get_connection_security(conn_name):
    """Get security type of an NM connection."""
    out, _, _ = run_cmd(
        ['nmcli', '-t', '-f', '802-11-wireless-security.key-mgmt',
         'connection', 'show', conn_name],
        timeout=5
    )
    if 'wpa-psk' in out:
        return 'wpa2'
    if 'sae' in out:
        return 'wpa3'
    if 'wep' in out:
        return 'wep'
    return 'open'


# ─────────────────────────────────────────────────────
#  CONNECT TO WIFI
# ─────────────────────────────────────────────────────

def connect_to_wifi(ssid, password=None, security='wpa2'):
    """Connect to a WiFi network (platform-agnostic)."""
    if PLATFORM == 'termux':
        return _connect_termux(ssid, password, security)
    else:
        return _connect_kali(ssid, password, security)


def _connect_termux(ssid, password, security):
    """Connect via Termux:API or Android cmd or wpa_cli."""
    cprint(Fore.CYAN, 'CONNECT', f'Connecting to "{ssid}" (Termux)...')

    # Map security
    if security in ('open', 'none'):
        sec_arg, key_arg = 'none', ''
    elif security == 'wep':
        sec_arg, key_arg = 'wep', password or ''
    else:
        sec_arg, key_arg = 'wpa', password or ''

    # Method 1: termux-wifi-connect
    out, err, rc = run_cmd(['termux-wifi-connect', ssid, sec_arg, key_arg], timeout=30)
    if rc == 0:
        cprint(Fore.GREEN, 'OK', 'Connected via termux-wifi-connect')
        time.sleep(3)
        return True

    # Method 2: Android cmd wifi
    cmd_sec = {'open': 'open', 'wep': 'wep', 'wpa': 'wpa2', 'wpa2': 'wpa2', 'wpa3': 'wpa3'}.get(security, 'wpa2')
    if password:
        out2, _, rc2 = run_cmd(['cmd', 'wifi', 'connect-network', ssid, cmd_sec, password], timeout=30)
    else:
        out2, _, rc2 = run_cmd(['cmd', 'wifi', 'connect-network', ssid, cmd_sec], timeout=30)
    if rc2 == 0:
        cprint(Fore.GREEN, 'OK', 'Connected via Android cmd')
        time.sleep(3)
        return True

    # Method 3: wpa_cli (root)
    if password:
        cprint(Fore.YELLOW, 'RETRY', 'Trying wpa_cli (requires root)...')
        wpa_cmd = f"""
add_network
set_network 0 ssid "{ssid}"
set_network 0 psk "{password}"
set_network 0 key_mgmt WPA-PSK
enable_network 0
save_config
"""
        try:
            proc = subprocess.Popen(
                ['wpa_cli', '-p', '/data/misc/wifi/sockets/', '-i', 'wlan0'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True
            )
            stdout, _ = proc.communicate(input=wpa_cmd, timeout=15)
            if 'OK' in stdout:
                cprint(Fore.GREEN, 'OK', 'Connected via wpa_cli')
                time.sleep(3)
                return True
        except Exception as e:
            cprint(Fore.RED, 'WPA_CLI', str(e))

    cprint(Fore.RED, 'FAIL', f'Could not connect to "{ssid}"')
    return False


def _connect_kali(ssid, password, security):
    """Connect via nmcli (Kali/Linux)."""
    cprint(Fore.CYAN, 'CONNECT', f'Connecting to "{ssid}" (Kali/Linux)...')

    # nmcli connection
    if not password or security == 'open':
        out, err, rc = run_cmd(
            ['nmcli', 'device', 'wifi', 'connect', ssid],
            timeout=30
        )
    else:
        out, err, rc = run_cmd(
            ['nmcli', 'device', 'wifi', 'connect', ssid, 'password', password],
            timeout=30
        )

    if rc == 0:
        cprint(Fore.GREEN, 'OK', 'Connected via nmcli')
        time.sleep(3)
        return True

    # Fallback: create connection manually
    conn_name = re.sub(r'[^a-zA-Z0-9_-]', '_', ssid)

    if password and security not in ('open', 'none'):
        # Delete existing if any
        run_cmd(['nmcli', 'connection', 'delete', conn_name], timeout=5)

        # Determine key-mgmt
        key_mgmt = 'sae' if security == 'wpa3' else 'wpa-psk'

        setup_cmds = [
            ['nmcli', 'connection', 'add', 'type', 'wifi', 'con-name', conn_name,
             'ifname', get_wifi_interface(), 'ssid', ssid],
            ['nmcli', 'connection', 'modify', conn_name,
             '802-11-wireless-security.key-mgmt', key_mgmt],
            ['nmcli', 'connection', 'modify', conn_name,
             '802-11-wireless-security.psk', password],
            ['nmcli', 'connection', 'up', conn_name],
        ]
        for cmd in setup_cmds:
            out, err, rc = run_cmd(cmd, timeout=15)
            if rc != 0:
                cprint(Fore.YELLOW, 'WARN', f'Step failed: {cmd[0]} {cmd[1]}: {err}')
                break
        else:
            cprint(Fore.GREEN, 'OK', 'Connected via nmcli (manual config)')
            time.sleep(3)
            return True
    else:
        # Open network
        run_cmd(['nmcli', 'connection', 'delete', conn_name], timeout=5)
        out, _, rc = run_cmd(
            ['nmcli', 'connection', 'add', 'type', 'wifi', 'con-name', conn_name,
             'ifname', get_wifi_interface(), 'ssid', ssid],
            timeout=15
        )
        if rc == 0:
            run_cmd(['nmcli', 'connection', 'up', conn_name], timeout=15)
            cprint(Fore.GREEN, 'OK', 'Connected (open network)')
            time.sleep(3)
            return True

    # Fallback: iw + wpa_supplicant
    cprint(Fore.YELLOW, 'RETRY', 'Trying iw + wpa_supplicant method...')
    if password:
        try:
            # Write wpa_supplicant config
            wpa_conf = f"""
network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
"""
            with open('/tmp/wpa_temp.conf', 'w') as f:
                f.write(wpa_conf)
            iface = get_wifi_interface()
            run_cmd(['wpa_supplicant', '-B', '-i', iface, '-c', '/tmp/wpa_temp.conf'], timeout=10)
            run_cmd(['dhclient', iface], timeout=15)
            cprint(Fore.GREEN, 'OK', 'Connected via wpa_supplicant')
            time.sleep(2)
            return True
        except Exception as e:
            cprint(Fore.RED, 'WPA_SUPPLICANT', str(e))

    cprint(Fore.RED, 'FAIL', f'Could not connect to "{ssid}"')
    return False


# ─────────────────────────────────────────────────────
#  CONNECTION STATUS
# ─────────────────────────────────────────────────────

def get_connection_info():
    """Get current connection info (platform-agnostic)."""
    if PLATFORM == 'termux':
        out, _, rc = run_cmd(['termux-wifi-connectioninfo'])
        if rc == 0 and out:
            try:
                return json.loads(out)
            except json.JSONDecodeError:
                pass
        return None
    else:
        # nmcli
        out, _, rc = run_cmd(['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IP4', 'connection', 'show', '--active'], timeout=5)
        if rc == 0 and out:
            for line in out.split('\n'):
                if not line.strip():
                    continue
                parts = line.split(':')
                if len(parts) >= 1 and parts[0]:
                    return {
                        'ssid': parts[0],
                        'rssi': int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0,
                        'security': parts[2] if len(parts) > 2 else '?',
                        'ip': parts[3] if len(parts) > 3 else '?',
                    }
        return None


def wait_for_connection(timeout=30):
    """Wait until WiFi is connected and has an IP."""
    start = time.time()
    while time.time() - start < timeout:
        info = get_connection_info()
        if info:
            ssid = info.get('ssid', '')
            ip = info.get('ip', '')
            if ssid and (ip or PLATFORM == 'termux'):
                return info
        time.sleep(2)
    return None


# ─────────────────────────────────────────────────────
#  DISPLAY HELPERS
# ─────────────────────────────────────────────────────

def display_available(networks):
    """Show available networks in a formatted table."""
    print(f"\n{Fore.CYAN}╔══════════════════════════════════════════════════════════╗")
    print(f"║           AVAILABLE WIFI NETWORKS                        ║")
    print(f"╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}")

    if not networks:
        print(f"  {Fore.YELLOW}No networks found. Check WiFi and permissions.{Style.RESET_ALL}")
        return

    print(f"\n  {'#':<3} {'SSID':<30} {'CH':<4} {'RSSI':<6} {'SEC':<8} {'BSSID'}")
    print(f"  {'-'*3} {'-'*30} {'-'*4} {'-'*6} {'-'*8} {'-'*17}")
    for i, n in enumerate(networks):
        ssid = n['ssid'][:28]
        ch = n.get('channel', '?')
        rssi = n.get('rssi', 0)
        sec = n.get('security', '?')
        bssid = n.get('bssid', '')
        bars = _signal_bars(rssi)
        print(f"  {i:<3} {Fore.GREEN}{ssid:<28}{Style.RESET_ALL} {ch:<4} {bars:<4} {sec:<8} {bssid}")
    print()


def display_saved(saved):
    """Show saved networks."""
    print(f"\n{Fore.CYAN}╔══════════════════════════════════════════════════════════╗")
    print(f"║           SAVED WIFI NETWORKS                            ║")
    print(f"╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}")

    if not saved:
        print(f"  {Fore.YELLOW}No saved networks found.{Style.RESET_ALL}")
        return

    print(f"\n  {'S#':<3} {'SSID':<30} {'SEC':<10} {'PASSWORD':<25}")
    print(f"  {'-'*3} {'-'*30} {'-'*10} {'-'*25}")
    for i, n in enumerate(saved):
        ssid = n['ssid'][:28]
        sec = n.get('security', '?')
        pwd = n.get('password') or '(unknown)'
        pwd_display = pwd[:23] if pwd else '(unknown)'
        print(f"  {i:<3} {Fore.YELLOW}{ssid:<28}{Style.RESET_ALL} {sec:<10} {Fore.MAGENTA}{pwd_display:<25}{Style.RESET_ALL}")
    print()


def _signal_bars(rssi):
    if rssi >= -50:
        return '▂▄▆█'
    elif rssi >= -60:
        return '▂▄▆ '
    elif rssi >= -70:
        return '▂▄  '
    elif rssi >= -80:
        return '▂   '
    return '    '


# ─────────────────────────────────────────────────────
#  SELECT NETWORK INTERACTIVE
# ─────────────────────────────────────────────────────

def select_network_interactive(available, saved):
    """Prompt user to pick a network."""
    print(f"\n{Fore.CYAN}╔══════════════════════════════════════════════════════════╗")
    print(f"║           SELECT TARGET NETWORK                            ║")
    print(f"╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}")

    print(f"\n  {Fore.GREEN}Options:{Style.RESET_ALL}")
    print(f"    • Enter a number (0, 1, 2...) → pick from Available list")
    print(f"    • Enter S<number> (S0, S1...)  → pick from Saved networks")
    print(f"    • Type a direct SSID name")
    print(f"    • Press Enter to skip (use current connection)")
    print()

    while True:
        try:
            choice = input(f"  {Fore.CYAN}Choice:{Style.RESET_ALL} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None, None, None

        if not choice:
            info = get_connection_info()
            if info and info.get('ssid'):
                ssid = info['ssid']
                cprint(Fore.GREEN, 'USE', f'Using current connection: "{ssid}"')
                return ssid, None, None
            if PLATFORM != 'termux':
                cprint(Fore.YELLOW, 'INFO', 'No active connection. You can still monitor.')
                return None, None, None
            cprint(Fore.YELLOW, 'INFO', 'No current connection.')
            continue

        # Saved: S<number>
        if choice.upper().startswith('S') and choice[1:].isdigit():
            idx = int(choice[1:])
            if 0 <= idx < len(saved):
                net = saved[idx]
                cprint(Fore.GREEN, 'SELECT', f'Saved: "{net["ssid"]}"')
                return net['ssid'], net.get('password'), net.get('security', 'wpa2')
            else:
                cprint(Fore.RED, 'ERROR', f'S{idx} out of range')
                continue

        # Number from available
        if choice.isdigit():
            idx = int(choice)
            if 0 <= idx < len(available):
                net = available[idx]
                pw = input(f"  {Fore.CYAN}Password for \"{net['ssid']}\" (Enter = open):{Style.RESET_ALL} ").strip()
                return net['ssid'], pw if pw else None, net.get('security', 'wpa2')
            else:
                cprint(Fore.RED, 'ERROR', f'{idx} out of range')
                continue

        # Direct SSID
        pw = input(f"  {Fore.CYAN}Password for \"{choice}\" (Enter = open):{Style.RESET_ALL} ").strip()
        sec = input(f"  {Fore.CYAN}Security [open/wpa2/wpa3] (default=wpa2):{Style.RESET_ALL} ").strip() or 'wpa2'
        return choice, pw if pw else None, sec


# ─────────────────────────────────────────────────────
#  TRAFFIC MONITORING
# ─────────────────────────────────────────────────────

APP_DNS_SIGNATURES = {
    # Social
    'facebook.com': 'Facebook', 'fbcdn.net': 'Facebook',
    'instagram.com': 'Instagram', 'cdninstagram.com': 'Instagram',
    'twitter.com': 'X/Twitter', 'x.com': 'X/Twitter', 't.co': 'X/Twitter', 'twimg.com': 'X/Twitter',
    'linkedin.com': 'LinkedIn',
    'snapchat.com': 'Snapchat', 'sc-t.com': 'Snapchat',
    'tiktok.com': 'TikTok', 'tiktokcdn.com': 'TikTok',
    'pinterest.com': 'Pinterest',
    'reddit.com': 'Reddit', 'redditmedia.com': 'Reddit',
    'telegram.org': 'Telegram', 't.me': 'Telegram',
    'whatsapp.net': 'WhatsApp', 'whatsapp.com': 'WhatsApp',
    # Search/Google
    'google.com': 'Google Search', 'googleapis.com': 'Google APIs',
    'gstatic.com': 'Google Static', 'youtube.com': 'YouTube',
    'ytimg.com': 'YouTube', 'googlevideo.com': 'YouTube',
    'bing.com': 'Bing', 'duckduckgo.com': 'DuckDuckGo',
    # Streaming
    'netflix.com': 'Netflix', 'nflxvideo.net': 'Netflix',
    'spotify.com': 'Spotify', 'scdn.co': 'Spotify',
    'twitch.tv': 'Twitch', 'jtvnw.net': 'Twitch',
    # Messaging
    'discord.com': 'Discord', 'discordapp.net': 'Discord',
    'signal.org': 'Signal', 'slack.com': 'Slack',
    'msedge.net': 'Microsoft Edge',
    # Shopping
    'amazon.com': 'Amazon', 'amazonaws.com': 'AWS',
    'ebay.com': 'eBay', 'aliexpress.com': 'AliExpress', 'shopify.com': 'Shopify',
    # Productivity
    'outlook.com': 'Outlook', 'office.com': 'Microsoft 365',
    'office365.com': 'Microsoft 365', 'live.com': 'Microsoft Live',
    'icloud.com': 'Apple iCloud', 'apple.com': 'Apple Services',
    'maps.googleapis.com': 'Google Maps',
    # AI
    'openai.com': 'ChatGPT/OpenAI', 'anthropic.com': 'Claude',
    'perplexity.ai': 'Perplexity AI',
    # Video/Meetings
    'zoom.us': 'Zoom', 'meet.google.com': 'Google Meet',
    'teams.microsoft.com': 'Microsoft Teams',
    # Dev
    'github.com': 'GitHub', 'githubusercontent.com': 'GitHub',
    'gitlab.com': 'GitLab', 'stackoverflow.com': 'Stack Overflow',
    'cloudflare.com': 'Cloudflare',
}


def identify_app_from_dns(domain):
    domain = domain.lower().strip('.')
    for pattern, app_name in APP_DNS_SIGNATURES.items():
        if domain == pattern or domain.endswith('.' + pattern):
            return app_name
    return None


def extract_search_from_url(url):
    patterns = [
        (r'google\.[^/]+/search\?.*[?&]q=([^&]+)', 'Google'),
        (r'bing\.[^/]+/search\?.*[?&]q=([^&]+)', 'Bing'),
        (r'duckduckgo\.com/[?&]q=([^&]+)', 'DuckDuckGo'),
        (r'youtube\.com/results\?.*[?&]search_query=([^&]+)', 'YouTube'),
        (r'search\.yahoo\.[^/]+/search\?.*[?&]p=([^&]+)', 'Yahoo'),
        (r'baidu\.[^/]+/s\?.*[?&]wd=([^&]+)', 'Baidu'),
        (r'en\.wikipedia\.org/wiki/([^&]+)', 'Wikipedia'),
    ]
    for pattern, engine in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            try:
                from urllib.parse import unquote
                query = unquote(match.group(1).replace('+', ' '))
                return engine, query
            except Exception:
                return engine, match.group(1)
    return None, None


def log_packet(packet):
    if not packet or not packet.haslayer(IP):
        return
    ip = packet[IP]
    src = ip.src
    dst = ip.dst

    # DNS queries
    if packet.haslayer(DNS) and packet.haslayer(DNSQR):
        dns = packet[DNS]
        if dns.qr == 0:
            qname = dns.qd.qname.decode('utf-8', errors='replace').rstrip('.')
            app = identify_app_from_dns(qname)
            tag = f"DNS: {app}" if app else "DNS"
            cprint(Fore.YELLOW, tag, f"{qname}  ({src} -> {dst})")
            return

    # HTTP
    if packet.haslayer(TCP) and packet.haslayer(Raw):
        try:
            raw = packet[Raw].load.decode('utf-8', errors='replace')
            if raw.startswith(('GET ', 'POST ', 'PUT ', 'DELETE ', 'HEAD ')):
                lines = raw.split('\r\n')
                method, path, _ = lines[0].split(' ', 2)
                host = ''
                for line in lines:
                    if line.lower().startswith('host:'):
                        host = line.split(': ', 1)[1]
                        break
                url = f"http://{host}{path}"
                engine, query = extract_search_from_url(url)
                if query:
                    cprint(Fore.GREEN, f'SEARCH: {engine}', f'"{query}"  ({src})')
                else:
                    app = identify_app_from_dns(host)
                    tag = f"HTTP: {app}" if app else "HTTP"
                    cprint(Fore.GREEN, tag, f"{method} {url}  ({src})")
                return
        except (UnicodeDecodeError, ValueError, IndexError):
            pass

    # HTTPS SNI
    if packet.haslayer(TCP) and packet.haslayer(Raw):
        try:
            raw = bytes(packet[Raw].load)
            if len(raw) > 5 and raw[0] == 0x16 and raw[1] == 0x03:
                loc = raw.find(b'\x00\x00')
                if loc > 0:
                    s = raw.find(b'\x00\x00', loc + 40)
                    if s > 0:
                        s += 2
                        l = struct.unpack('>H', raw[s:s+2])[0]
                        s += 2
                        if s + l < len(raw) and raw[s:s+1] == b'\x00':
                            s += 5
                            l2 = struct.unpack('>H', raw[s:s+2])[0]
                            s += 2
                            name = raw[s:s+l2].decode('utf-8', errors='replace')
                            app = identify_app_from_dns(name)
                            tag = f"HTTPS: {app}" if app else "HTTPS"
                            cprint(Fore.MAGENTA, tag, f"{name} ({src} -> {dst})")
        except (IndexError, struct.error, UnicodeDecodeError, ValueError):
            pass


def start_monitoring(interface=None):
    """Start packet sniffing with scapy."""
    if not HAVE_SCAPY:
        cprint(Fore.RED, 'ERROR', 'scapy not installed. pip install scapy')
        return

    if interface is None:
        interface = get_wifi_interface()

    info = get_connection_info()
    if info:
        ssid = info.get('ssid', '?')
        ip = info.get('ip', '?')
        cprint(Fore.CYAN, 'MONITOR', f'Monitoring on {interface} — "{ssid}" ({ip})')
    else:
        cprint(Fore.CYAN, 'MONITOR', f'Monitoring on {interface} (no active connection)')

    msg = 'Listening for DNS, HTTP, HTTPS (SNI)... Ctrl+C to stop.'
    if PLATFORM == 'termux':
        msg += ' Run with tsu for raw packet access.'
    cprint(Fore.CYAN, 'MONITOR', msg)

    try:
        sniff(iface=interface, prn=log_packet, store=False, count=0)
    except PermissionError:
        cprint(Fore.RED, 'ERROR', 'Permission denied. Need root.')
        if PLATFORM == 'termux':
            cprint(Fore.YELLOW, 'HINT', 'Run: tsu python3 ' + os.path.basename(sys.argv[0]))
        else:
            cprint(Fore.YELLOW, 'HINT', 'Run: sudo python3 ' + os.path.basename(sys.argv[0]))
    except KeyboardInterrupt:
        cprint(Fore.CYAN, 'STOP', 'Monitoring stopped.')
    except Exception as e:
        cprint(Fore.RED, 'ERROR', str(e))


# ─────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Universal WiFi Monitor — Kali Linux & Termux (Android)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Platform detected: {PLATFORM.upper()}

Examples:
  python3 {sys.argv[0]}                           # Full interactive (scan → connect → monitor)
  python3 {sys.argv[0]} --scan-only                 # Scan and show networks
  python3 {sys.argv[0]} --saved                     # Show saved networks
  python3 {sys.argv[0]} --ssid MyWiFi --password x  # Direct connect + monitor
  sudo python3 {sys.argv[0]}                        # Kali with root
  tsu python3 {sys.argv[0]}                         # Termux with root
        """
    )
    parser.add_argument('--ssid', help='Connect directly to this SSID')
    parser.add_argument('--password', help='Password for the SSID')
    parser.add_argument('--security', default='wpa2', choices=['open', 'wep', 'wpa', 'wpa2', 'wpa3'],
                        help='Security type (default: wpa2)')
    parser.add_argument('--scan-only', action='store_true', help='Scan and display networks, then exit')
    parser.add_argument('--saved', action='store_true', help='Show saved networks, then exit')
    parser.add_argument('--interface', '-i', default=None, help='Interface to monitor (auto-detect if omitted)')
    parser.add_argument('--no-monitor', action='store_true', help='Connect only, no monitoring')
    parser.add_argument('--interface-list', action='store_true', help='List wireless interfaces and exit')

    args = parser.parse_args()

    # ── Banner ──
    print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════╗
║         Universal WiFi Monitor v3.0                     ║
║         Platform: {PLATFORM.upper():<33}║
║         Scan → Connect → Monitor                        ║
╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
""")

    # ── Interface list ──
    if args.interface_list:
        if PLATFORM == 'termux':
            cprint(Fore.YELLOW, 'INFO', 'Termux default interface: wlan0')
        else:
            iface = get_wifi_interface()
            cprint(Fore.GREEN, 'INTERFACE', f'Detected: {iface}')
            out, _, _ = run_cmd(['iwconfig'], timeout=5)
            print(out if out else '(no wireless extensions found)')
        return

    # ── Dependencies ──
    check_dependencies()

    # ── Enable WiFi ──
    wifi_enable()

    # ── Scan ──
    available = scan_networks()
    display_available(available)

    if args.scan_only:
        return

    # ── Saved ──
    saved = list_saved_networks()
    if saved:
        display_saved(saved)
    else:
        print(f"  {Fore.YELLOW}No saved networks found.{Style.RESET_ALL}\n")

    if args.saved:
        return

    # ── Target ──
    ssid = args.ssid
    password = args.password
    security = args.security

    if not ssid:
        ssid, password, security = select_network_interactive(available, saved)
        if not ssid:
            print(f"\n  {Fore.YELLOW}No network selected.{Style.RESET_ALL}")
            # Still allow monitoring without connection
            if not args.no_monitor:
                print(f"  {Fore.YELLOW}Starting monitor on current interface anyway...{Style.RESET_ALL}")
                start_monitoring(args.interface)
            return

    # ── Connect ──
    connected = connect_to_wifi(ssid, password, security)
    if not connected:
        cprint(Fore.RED, 'FAIL', 'Connection failed.')

    # ── Verify ──
    info = wait_for_connection(timeout=15)
    if info:
        ssid_show = info.get('ssid', ssid)
        ip = info.get('ip', '?')
        cprint(Fore.GREEN, 'OK', f'Connected to "{ssid_show}" — IP: {ip}')
    elif connected:
        cprint(Fore.YELLOW, 'WARN', 'Connection seems OK but could not verify.')
    else:
        cprint(Fore.YELLOW, 'WARN', 'Not connected. Monitoring raw interface anyway.')

    # ── Monitor ──
    if not args.no_monitor:
        print(f"\n{Fore.CYAN}╔══════════════════════════════════════════════════════════╗")
        print(f"║           MONITORING TRAFFIC                              ║")
        print(f"╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}\n")
        start_monitoring(args.interface)
    else:
        cprint(Fore.GREEN, 'DONE', 'Connected. Monitoring skipped (--no-monitor).')


if __name__ == '__main__':
    main()
