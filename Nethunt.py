#!/usr/bin/env python3
"""
Termux Traffic Monitor - Packet Capture & App Traffic Analyzer
Author: HackerAI
Target: Android Termux environment
Use: Monitor HTTP/HTTPS traffic, DNS queries, and app connections
      on a connected wifi/hotspot interface.

Requirements:
  pip install scapy colorama
  pkg install tcpdump tsu  (for root mode)
  OR install PCAPdroid from F-Droid (for non-root mode)

Authorized use only. Ensure proper scope.
"""

import argparse
import socket
import struct
import time
import re
import subprocess
import sys
import os
from datetime import datetime
from collections import defaultdict

# Optional imports - graceful fallback if not installed
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    HAVE_COLORAMA = True
except ImportError:
    HAVE_COLORAMA = False
    # Dummy colorama
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ''
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ''

try:
    from scapy.all import sniff, IP, TCP, UDP, DNS, DNSQR, HTTPRequest, Raw
    from scapy.layers.http import HTTP  # scapy-http
    HAVE_SCAPY = True
except ImportError:
    HAVE_SCAPY = False


# ============================================================
#  COLOR / THEMING
# ============================================================
C = {
    'INFO': Fore.CYAN,
    'HTTP': Fore.GREEN,
    'DNS': Fore.YELLOW,
    'APP': Fore.MAGENTA,
    'ERR': Fore.RED,
    'HOST': Fore.BLUE,
    'RST': Style.RESET_ALL,
}


def cprintf(color, tag, msg):
    """Color-print with timestamp."""
    ts = datetime.now().strftime('%H:%M:%S')
    if HAVE_COLORAMA:
        print(f"{Fore.WHITE}[{ts}]{C['RST']} {color}[{tag}]{C['RST']} {msg}")
    else:
        print(f"[{ts}] [{tag}] {msg}")


# ============================================================
#  DNS-BASED APP FINGERPRINTING (known DNS patterns)
# ============================================================
# Maps common DNS domains to likely app names
APP_DNS_SIGNATURES = {
    # Social Media
    'facebook.com': 'Facebook',
    'fbcdn.net': 'Facebook',
    'instagram.com': 'Instagram',
    'cdninstagram.com': 'Instagram',
    'twitter.com': 'X/Twitter',
    'x.com': 'X/Twitter',
    't.co': 'X/Twitter',
    'twimg.com': 'X/Twitter',
    'linkedin.com': 'LinkedIn',
    'snapchat.com': 'Snapchat',
    'sc-t.com': 'Snapchat',
    'tiktok.com': 'TikTok',
    'tiktokcdn.com': 'TikTok',
    'pinterest.com': 'Pinterest',
    'reddit.com': 'Reddit',
    'redditmedia.com': 'Reddit',
    'telegram.org': 'Telegram',
    't.me': 'Telegram',
    'whatsapp.net': 'WhatsApp',
    'whatsapp.com': 'WhatsApp',

    # Browsers / Search
    'google.com': 'Google Search',
    'googleapis.com': 'Google APIs',
    'gstatic.com': 'Google Static',
    'youtube.com': 'YouTube',
    'ytimg.com': 'YouTube',
    'googlevideo.com': 'YouTube',
    'bing.com': 'Bing Search',
    'duckduckgo.com': 'DuckDuckGo',

    # Streaming
    'netflix.com': 'Netflix',
    'nflxvideo.net': 'Netflix',
    'spotify.com': 'Spotify',
    'scdn.co': 'Spotify',
    'twitch.tv': 'Twitch',
    'jtvnw.net': 'Twitch',

    # Messaging
    'discord.com': 'Discord',
    'discordapp.net': 'Discord',
    'signal.org': 'Signal',
    'slack.com': 'Slack',
    'msedge.net': 'Microsoft Edge',

    # Commerce
    'amazon.com': 'Amazon',
    'amazonaws.com': 'AWS (various)',
    'ebay.com': 'eBay',
    'aliexpress.com': 'AliExpress',
    'shopify.com': 'Shopify',

    # Email / Productivity
    'outlook.com': 'Outlook',
    'office.com': 'Microsoft 365',
    'office365.com': 'Microsoft 365',
    'live.com': 'Microsoft Live',
    'icloud.com': 'Apple iCloud',
    'apple.com': 'Apple Services',

    # Maps / Location
    'maps.googleapis.com': 'Google Maps',
    'maps.apple.com': 'Apple Maps',

    # AI / Chat
    'openai.com': 'ChatGPT/OpenAI',
    'anthropic.com': 'Claude/Anthropic',
    'perplexity.ai': 'Perplexity AI',

    # Video / Chat
    'zoom.us': 'Zoom',
    'zoomgov.com': 'Zoom',
    'meet.google.com': 'Google Meet',
    'teams.microsoft.com': 'Microsoft Teams',
    'skype.com': 'Skype',

    # Cloud / Dev
    'github.com': 'GitHub',
    'githubusercontent.com': 'GitHub',
    'gitlab.com': 'GitLab',
    'stackoverflow.com': 'Stack Overflow',
    'docker.com': 'Docker',
    'cloudflare.com': 'Cloudflare',
}


def identify_app_from_dns(domain):
    """Identify likely app from DNS query domain."""
    domain = domain.lower().strip('.')
    for pattern, app_name in APP_DNS_SIGNATURES.items():
        if domain == pattern or domain.endswith('.' + pattern):
            return app_name
    return None


def extract_search_from_url(url):
    """Extract search query from search engine URLs."""
    patterns = [
        # Google
        (r'google\.[^/]+/search\?.*[?&]q=([^&]+)', 'Google'),
        # Bing
        (r'bing\.[^/]+/search\?.*[?&]q=([^&]+)', 'Bing'),
        # DuckDuckGo
        (r'duckduckgo\.com/[?&]q=([^&]+)', 'DuckDuckGo'),
        # YouTube
        (r'youtube\.com/results\?.*[?&]search_query=([^&]+)', 'YouTube'),
        # Yahoo
        (r'search\.yahoo\.[^/]+/search\?.*[?&]p=([^&]+)', 'Yahoo'),
        # Baidu
        (r'baidu\.[^/]+/s\?.*[?&]wd=([^&]+)', 'Baidu'),
        # Wikipedia
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


# ============================================================
#  MODE 1: ROOT - Scapy Packet Sniffer
# ============================================================

def log_packet_info(packet):
    """Extract and display relevant info from a sniffed packet."""
    if not packet or not packet.haslayer(IP):
        return

    ip = packet[IP]
    src = ip.src
    dst = ip.dst
    proto = ip.proto
    length = len(packet)

    # ---- DNS Queries ----
    if packet.haslayer(DNS) and packet.haslayer(DNSQR):
        dns = packet[DNS]
        if dns.qr == 0:  # Query
            qname = dns.qd.qname.decode('utf-8', errors='replace').rstrip('.')
            app = identify_app_from_dns(qname)
            tag = f"DNS: {app}" if app else "DNS Query"
            cprintf(C['DNS'], tag, f"{qname}  ({src} -> {dst})")
            return

    # ---- HTTP Requests ----
    if packet.haslayer(TCP) and packet.haslayer(Raw):
        try:
            raw = packet[Raw].load.decode('utf-8', errors='replace')
            # Check for HTTP request line
            if raw.startswith(('GET ', 'POST ', 'PUT ', 'DELETE ', 'HEAD ', 'OPTIONS ')):
                lines = raw.split('\r\n')
                request_line = lines[0]
                method, path, _ = request_line.split(' ', 2)
                host = ''
                for line in lines:
                    if line.lower().startswith('host:'):
                        host = line.split(': ', 1)[1]
                        break

                url = f"http://{host}{path}"
                engine, query = extract_search_from_url(url)
                if query:
                    cprintf(C['HTTP'], f"SEARCH: {engine}", f'"{query}"  ({src})')
                else:
                    app = identify_app_from_dns(host)
                    tag = f"HTTP: {app}" if app else "HTTP Request"
                    cprintf(C['HTTP'], tag, f"{method} {url}  ({src})")
                return
        except (UnicodeDecodeError, ValueError, IndexError):
            pass

    # ---- HTTPS / TLS SNI ----
    if packet.haslayer(TCP) and packet.haslayer(Raw):
        try:
            raw = packet[Raw].load
            # TLS ClientHello - extract SNI
            if raw[0] == 0x16 and raw[1] == 0x03:  # TLS handshake
                # Simple SNI extraction
                idx = raw.find(b'\x00\x00')  # Start of extensions
                if idx > 0:
                    sni_start = raw.find(b'\x00\x00', idx + 40)
                    if sni_start > 0:
                        sni_start += 2
                        sni_len = struct.unpack('>H', raw[sni_start:sni_start+2])[0]
                        sni_start += 2
                        if sni_start + sni_len < len(raw):
                            if raw[sni_start:sni_start+1] == b'\x00':
                                sni_start += 5
                                sni_len2 = struct.unpack('>H', raw[sni_start:sni_start+2])[0]
                                sni_start += 2
                                sni_name = raw[sni_start:sni_start+sni_len2].decode('utf-8', errors='replace')
                                app = identify_app_from_dns(sni_name)
                                tag = f"HTTPS: {app}" if app else "HTTPS"
                                cprintf(C['APP'], tag, f"{sni_name}  ({src} -> {dst})")
                                return
        except (IndexError, struct.error, UnicodeDecodeError):
            pass


def sniff_root(interface='wlan0', packet_count=0):
    """Start scapy sniffing (requires root/tsu)."""
    if not HAVE_SCAPY:
        cprintf(C['ERR'], 'ERROR', 'scapy is not installed. Run: pip install scapy')
        sys.exit(1)

    cprintf(C['INFO'], 'START', f'Sniffing on {interface}... (Ctrl+C to stop)')
    cprintf(C['INFO'], 'NOTE', 'This requires root. Run with: tsu python3 termux_traffic_monitor.py')

    try:
        sniff(
            iface=interface,
            prn=log_packet_info,
            store=False,
            count=packet_count if packet_count > 0 else 0,
        )
    except PermissionError:
        cprintf(C['ERR'], 'ERROR', 'Permission denied. Run with tsu (root) for raw packet capture.')
        cprintf(C['INFO'], 'HINT', 'Try: tsu python3 termux_traffic_monitor.py --mode root')
    except KeyboardInterrupt:
        cprintf(C['INFO'], 'STOP', 'Sniffing stopped by user.')
    except Exception as e:
        cprintf(C['ERR'], 'ERROR', f'{e}')


# ============================================================
#  MODE 2: PCAPdroid UDP Receiver (No Root)
# ============================================================

def start_pcapdroid_udp_receiver(port=5555):
    """
    Receive live PCAP data via UDP from PCAPdroid.

    Setup:
    1. Install PCAPdroid from F-Droid
    2. In PCAPdroid -> Settings -> PCAP dumper:
       - Enable "UDP Exporter"
       - Set target: 127.0.0.1:{port}
    3. Start PCAPdroid capture
    4. Run this mode
    """
    cprintf(C['INFO'], 'START',
            f'Listening for PCAPdroid UDP stream on 127.0.0.1:{port}...')
    cprintf(C['INFO'], 'SETUP',
            'Configure PCAPdroid: Settings > PCAP dumper > UDP Exporter > 127.0.0.1:5555')

    # Set up UDP socket to receive PCAP data
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(30.0)

    try:
        sock.bind(('127.0.0.1', port))
        cprintf(C['INFO'], 'READY', 'Waiting for PCAPdroid data...')
    except OSError as e:
        cprintf(C['ERR'], 'ERROR', f'Cannot bind to port {port}: {e}')
        sys.exit(1)

    try:
        while True:
            try:
                data, addr = sock.recvfrom(65535)
                ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                # Parse minimal data from PCAPdroid's UDP format
                # Format: [src_ip] [dst_ip] [src_port] [dst_port] [proto] [app_name] [dns/host]
                line = data.decode('utf-8', errors='replace').strip()
                if not line:
                    continue

                # PCAPdroid UDP format varies by version; try to parse
                parts = line.split()

                # Try to extract meaningful info
                app_name = 'Unknown'
                domain = ''
                for part in parts:
                    if '=' in part:
                        key, val = part.split('=', 1)
                        if key.lower() in ('app', 'app_name', 'uid_name'):
                            app_name = val
                        elif key.lower() in ('host', 'dns', 'sni', 'domain'):
                            domain = val

                # Also try to match from known patterns
                for part in parts:
                    for pattern, name in APP_DNS_SIGNATURES.items():
                        if pattern in part.lower():
                            app_name = name
                            break

                if domain:
                    cprintf(C['APP'], f'APP: {app_name}', f'{domain}  (from {addr[0]})')
                else:
                    cprintf(C['APP'], 'PACKET', f'{" | ".join(parts[:6])}  [{app_name}]')

            except socket.timeout:
                cprintf(C['INFO'], 'WAIT', 'No data received in 30s. Ensure PCAPdroid is running...')
            except UnicodeDecodeError:
                cprintf(C['ERR'], 'PARSE', 'Received non-text data (PCAP binary)')

    except KeyboardInterrupt:
        cprintf(C['INFO'], 'STOP', 'UDP receiver stopped.')
    finally:
        sock.close()


# ============================================================
#  MODE 3: tcpdump + Python parser (Root alternative)
# ============================================================

def capture_with_tcpdump(interface='wlan0', output_file=None):
    """Use tcpdump as backend, parse with Python."""
    if output_file is None:
        output_file = f'/sdcard/capture_{int(time.time())}.pcap'

    cprintf(C['INFO'], 'TCPDUMP', f'Starting tcpdump on {interface}...')
    cprintf(C['INFO'], 'OUTPUT', f'Writing to {output_file}')

    cmd = [
        'tcpdump',
        '-i', interface,
        '-w', output_file,
        '-s', '0',           # Full packet capture
        '-v',                # Verbose
        'port 53 or port 80 or port 443',  # DNS + HTTP + HTTPS
    ]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        cprintf(C['INFO'], 'RUNNING', f'tcpdump PID: {proc.pid}')
        cprintf(C['INFO'], 'HINT', 'Press Ctrl+C to stop and analyze')

        # Display live summary from stderr
        while True:
            line = proc.stderr.readline().decode('utf-8', errors='replace').strip()
            if line:
                # Extract useful bits
                if 'IP ' in line or 'DNS' in line or 'HTTP' in line:
                    print(f"  {Fore.YELLOW}{line}{Style.RESET_ALL}")

    except KeyboardInterrupt:
        cprintf(C['INFO'], 'STOP', 'Stopping tcpdump...')
        proc.terminate()
        proc.wait()
        cprintf(C['INFO'], 'SAVED', f'PCAP saved to {output_file}')
        cprintf(C['INFO'], 'ANALYZE', f'Run: tshark -r {output_file}  or  transfer to PC')


# ============================================================
#  MODE 4: Local-only monitor (non-root, limited scope)
# ============================================================

def monitor_local_traffic():
    """
    Monitor only the traffic generated from within Termux itself.
    This is limited (no other app traffic) but works without root.
    Uses socket-level monitoring of DNS lookups.
    """
    cprintf(C['INFO'], 'LOCAL', 'Monitoring Termux local DNS and HTTP requests...')
    cprintf(C['INFO'], 'NOTE', 'This only captures traffic FROM Termux, not other apps.')

    # Patch socket.getaddrinfo to log DNS lookups
    original_getaddrinfo = socket.getaddrinfo

    def logging_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        app = identify_app_from_dns(host)
        tag = f"DNS: {app}" if app else "DNS"
        cprintf(C['DNS'], tag, f'{host}')
        return original_getaddrinfo(host, port, family, type, proto, flags)

    socket.getaddrinfo = logging_getaddrinfo

    # Patch urllib if available
    try:
        from urllib.request import urlopen as original_urlopen
        from urllib.request import Request

        def logging_urlopen(url, *args, **kwargs):
            engine, query = extract_search_from_url(url)
            if query:
                cprintf(C['HTTP'], f'SEARCH: {engine}', f'"{query}"')
            else:
                cprintf(C['HTTP'], 'HTTP Request', f'{url}')
            return original_urlopen(url, *args, **kwargs)

        # Monkey-patch (will affect this Python process)
        import urllib.request
        urllib.request.urlopen = logging_urlopen
    except ImportError:
        pass

    cprintf(C['INFO'], 'MONITORING', 'Ready. Commands run in this terminal will be logged.')
    cprintf(C['INFO'], 'HINT', 'Open another Termux session and browse with curl/wget to test.')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cprintf(C['INFO'], 'STOP', 'Monitoring stopped.')
        socket.getaddrinfo = original_getaddrinfo


# ============================================================
#  SETUP HELPER
# ============================================================

def show_setup_instructions():
    """Print setup instructions for all modes."""
    print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════╗
║         Termux Traffic Monitor - Setup Guide              ║
╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.YELLOW}[ REQUIRED DEPENDENCIES ]{Style.RESET_ALL}
  pkg update && pkg upgrade
  pkg install python tsu tcpdump root-repo
  pip install scapy colorama

  # For HTTP layer parsing (optional but recommended)
  pip install scapy-http

{Fore.YELLOW}[ MODE: ROOT (Full Capture) ]{Style.RESET_ALL}
  Run: tsu python3 {sys.argv[0]} --mode root

  This captures ALL traffic on the wifi interface.
  Works best when your device acts as a hotspot.

{Fore.YELLOW}[ MODE: NON-ROOT (PCAPdroid) ]{Style.RESET_ALL}
  1. Install PCAPdroid from F-Droid
  2. Settings > PCAP dumper > UDP Exporter > ON
  3. Set target: 127.0.0.1:5555
  4. Start PCAPdroid capture
  5. Run: python3 {sys.argv[0]} --mode pcapdroid

{Fore.YELLOW}[ MODE: Hotspot Setup ]{Style.RESET_ALL}
  On your Android device:
  Settings > Hotspot & Tethering > Wi-Fi hotspot
  Connect target devices to this hotspot.
  All their traffic routes through your phone.

  Then run: tsu python3 {sys.argv[0]} --mode root

{Fore.YELLOW}[ TIPS ]{Style.RESET_ALL}
  - HTTPS traffic shows only domains (SNI), not URLs
  - HTTP traffic shows full URLs including search queries
  - Use PCAPdroid + its TLS decryption for HTTPS content
  - PCAP files can be analyzed with Wireshark/tshark on PC
""")


# ============================================================
#  MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='Termux Traffic Monitor - Packet Capture & App Traffic Analyzer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  tsu python3 termux_traffic_monitor.py --mode root
  python3 termux_traffic_monitor.py --mode pcapdroid
  python3 termux_traffic_monitor.py --mode tcpdump -i wlan0
  python3 termux_traffic_monitor.py --setup
        """
    )
    parser.add_argument('--mode', '-m',
                        choices=['root', 'pcapdroid', 'tcpdump', 'local'],
                        default='root',
                        help='Capture mode (default: root)')
    parser.add_argument('--interface', '-i',
                        default='wlan0',
                        help='Network interface (default: wlan0)')
    parser.add_argument('--port', '-p',
                        type=int, default=5555,
                        help='UDP port for PCAPdroid (default: 5555)')
    parser.add_argument('--output', '-o',
                        help='Output PCAP file path')
    parser.add_argument('--setup', '-s',
                        action='store_true',
                        help='Show setup instructions and exit')
    parser.add_argument('--packets', '-n',
                        type=int, default=0,
                        help='Number of packets to capture (0 = unlimited)')

    args = parser.parse_args()

    if args.setup:
        show_setup_instructions()
        sys.exit(0)

    print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════╗
║       Termux Traffic Monitor v1.0                 ║
║       Mode: {args.mode.upper():<29}║
╚══════════════════════════════════════════════════╝{Style.RESET_ALL}
""")

    if args.mode == 'root':
        sniff_root(args.interface, args.packets)
    elif args.mode == 'pcapdroid':
        start_pcapdroid_udp_receiver(args.port)
    elif args.mode == 'tcpdump':
        capture_with_tcpdump(args.interface, args.output)
    elif args.mode == 'local':
        monitor_local_traffic()


if __name__ == '__main__':
    main()
