#!/usr/bin/env python3
"""
Termux Pineapple - Open Hotspot with Device Monitoring
For authorized security assessments only.
"""

import os
import sys
import time
import json
import subprocess
import threading
import signal
import re
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================
AP_IFACE = "wlan0"         # Physical WiFi interface
AP_IP = "192.168.4.1"      # IP for the AP interface
AP_NET = "192.168.4"       # Subnet
AP_MASK = "255.255.255.0"
AP_CHANNEL = "6"

# Files
HOSTAPD_CONF = "/data/data/com.termux/files/home/hostapd.conf"
DNSMASQ_CONF = "/data/data/com.termux/files/home/dnsmasq.conf"
KNOWN_DEVICES_FILE = "/data/data/com.termux/files/home/.pineapple_known.json"

# ============================================================
# BANNER
# ============================================================
BANNER = r"""
    ________  ___
   /  _/ __ \/   \   Termux Pineapple
   / // /_/ / /| |   Open Hotspot Monitor
 _/__/ .___/ ___ |   Authorized Pentest Tool
  /_/_/     /_/  |_|
  v1.0 - No Password AP + Client Tracking
"""

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def run_cmd(cmd, timeout=10):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        proc = subprocess.Popen(
            cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(timeout=timeout)
        return proc.returncode, stdout.strip(), stderr.strip()
    except subprocess.TimeoutExpired:
        proc.kill()
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)


def check_root():
    """Check if we have root (required for hostapd)."""
    ret, out, err = run_cmd("id -u")
    if ret == 0 and out == "0":
        return True
    # Also try tsu
    ret, out, err = run_cmd("command -v tsu")
    if ret == 0:
        return True
    return False


def check_deps():
    """Check that required packages are installed."""
    deps = {
        "hostapd": "pkg install hostapd",
        "dnsmasq": "pkg install dnsmasq",
        "python": "pkg install python",
    }
    if not os.path.exists("/system/bin/ip") and not os.path.exists("/system/xbin/ip"):
        deps["tsu (or root)"] = "pkg install tsu"
    
    missing = []
    for dep, install_cmd in deps.items():
        ret, out, err = run_cmd(f"command -v {dep.split()[0]}")
        if ret != 0:
            missing.append((dep, install_cmd))
    
    return missing


def get_mac_vendor(mac):
    """Look up MAC vendor using the OUI database."""
    oui = mac.upper().replace(":", "")[:6]
    
    # Built-in common OUI database (compact)
    vendors = {
        "00037F": "Samsung", "0015E9": "Apple", "0016CB": "Apple",
        "001B63": "Apple", "001D4F": "Apple", "0021E9": "Apple",
        "002272": "Apple", "0023DF": "Apple", "0025BC": "Apple",
        "0026B0": "Apple", "0027B0": "Apple", "0028B0": "Apple",
        "003065": "Apple", "0030B0": "Apple", "0050F2": "Microsoft",
        "0050B0": "Intel", "00A0C9": "Intel", "000C29": "VMware",
        "005056": "VMware", "000569": "VMware", "001C42": "HTC",
        "00A0C6": "Cisco", "001B54": "Cisco", "000F66": "Cisco",
        "00155D": "ASUS", "001E8C": "ASUS", "000625": "Dell",
        "0018F3": "Dell", "001B78": "HP", "002481": "HP",
        "00037F": "Samsung", "001EE6": "Samsung", "002618": "Samsung",
        "00A091": "Nokia", "0021FE": "Nokia", "001D0F": "LG",
        "001A80": "LG", "001E10": "LG", "002181": "OnePlus",
        "002512": "Xiaomi", "00A050": "Xiaomi", "0018D1": "Sony",
        "00259E": "Sony", "0011B8": "Huawei", "001857": "Huawei",
        "0025A0": "Huawei", "00187A": "Motorola", "001E39": "Motorola",
        "000C6E": "Raspberry Pi", "B827EB": "Raspberry Pi",
        "DCA632": "Raspberry Pi", "E45F01": "Raspberry Pi",
        "000ED1": "Google/Nest", "001A11": "Google",
        "A885B2": "Google", "2462AB": "Amazon", "AC63BE": "Amazon",
        "74C246": "Amazon", "0017C8": "Netgear", "A021B7": "Netgear",
        "001E2A": "Netgear", "0023CD": "TP-Link", "50C7BF": "TP-Link",
        "14CFE2": "TP-Link", "00B0D0": "D-Link", "0015E9": "D-Link",
        "5C4979": "Ubiquiti", "00192F": "Ubiquiti", "00156D": "Ubiquiti",
        "F0B429": "Ubiquiti", "DCA632": "Espressif", "24B6FD": "Espressif",
        "ECFA00": "Espressif", "001583": "BlackBerry", "0001E6": "Acer",
        "0021C5": "Acer", "0019B9": "Lenovo", "0018FE": "Lenovo",
        "F8A963": "NVIDIA", "0018DE": "Microsoft/Xbox",
        "002622": "Fitbit", "0016A4": "Belkin", "009091": "Belkin",
    }
    
    return vendors.get(oui, "Unknown")


def get_hostname_from_lease(ip):
    """Try to get hostname from dnsmasq lease file."""
    lease_file = "/data/data/com.termux/files/home/dnsmasq.leases"
    if os.path.exists(lease_file):
        try:
            with open(lease_file, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 4 and parts[2] == ip:
                        return parts[3]  # hostname
        except:
            pass
    return None


def get_device_info(ip, mac):
    """Gather as much info as possible about a connected device."""
    info = {
        "ip": ip,
        "mac": mac,
        "vendor": get_mac_vendor(mac),
        "hostname": get_hostname_from_lease(ip) or "Unknown",
        "first_seen": datetime.now().strftime("%H:%M:%S"),
        "last_seen": datetime.now().strftime("%H:%M:%S"),
    }
    
    # Try reverse DNS lookup
    ret, out, err = run_cmd(f"nslookup {ip} 2>/dev/null | grep 'name =' | awk '{{print $4}}'")
    if out:
        info["hostname"] = out.rstrip(".")
    
    # Try to get NetBIOS name
    ret, out, err = run_cmd(f"nmblookup -A {ip} 2>/dev/null | grep '<00>' | head -1 | awk '{{print $1}}'")
    if out and out != ip:
        info["hostname"] = out
    
    return info


# ============================================================
# HOTSPOT MANAGEMENT
# ============================================================

def generate_hostapd_conf(ssid, iface=AP_IFACE, channel=AP_CHANNEL):
    """Generate hostapd.conf for an open (no password) AP."""
    conf = f"""interface={iface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=0
"""
    with open(HOSTAPD_CONF, "w") as f:
        f.write(conf)
    print(f"[+] hostapd config written: SSID='{ssid}' (open, ch{channel})")


def generate_dnsmasq_conf():
    """Generate dnsmasq.conf for DHCP on AP network."""
    conf = f"""interface=ap0
dhcp-range={AP_NET}.2,{AP_NET}.100,255.255.255.0,24h
dhcp-option=3,{AP_IP}
dhcp-option=6,{AP_IP}
dhcp-leasefile=/data/data/com.termux/files/home/dnsmasq.leases
log-dhcp
bind-interfaces
"""
    with open(DNSMASQ_CONF, "w") as f:
        f.write(conf)
    print("[+] dnsmasq config written")


def interface_up(iface, ip):
    """Bring up an interface with IP."""
    run_cmd(f"ip link set {iface} up")
    run_cmd(f"ip addr add {ip}/24 dev {iface}")
    print(f"[+] Interface {iface} up at {ip}")


def start_hotspot():
    """Start hostapd and dnsmasq processes."""
    print("[*] Starting hostapd...")
    proc_h = subprocess.Popen(
        ["hostapd", HOSTAPD_CONF],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    
    print("[*] Starting dnsmasq...")
    proc_d = subprocess.Popen(
        ["dnsmasq", "-C", DNSMASQ_CONF, "--no-daemon"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    # Actually run dnsmasq as daemon
    run_cmd(f"dnsmasq -C {DNSMASQ_CONF}")
    
    return proc_h


def stop_hotspot(proc_h=None):
    """Kill AP processes and clean up."""
    print("\n[*] Stopping hotspot...")
    if proc_h:
        proc_h.terminate()
    run_cmd("killall hostapd 2>/dev/null")
    run_cmd("killall dnsmasq 2>/dev/null")
    run_cmd(f"ip link set ap0 down 2>/dev/null")
    run_cmd(f"ip addr flush dev ap0 2>/dev/null")
    # Restore WiFi
    run_cmd(f"ip link set {AP_IFACE} down 2>/dev/null")
    time.sleep(0.5)
    run_cmd(f"ip link set {AP_IFACE} up 2>/dev/null")
    print("[+] Cleanup done")


# ============================================================
# DEVICE MONITORING
# ============================================================

def scan_arp():
    """Parse /proc/net/arp to find connected devices."""
    devices = {}
    try:
        with open("/proc/net/arp", "r") as f:
            lines = f.readlines()
        for line in lines[1:]:  # skip header
            parts = line.split()
            if len(parts) >= 4 and parts[3] != "00:00:00:00:00:00":
                ip = parts[0]
                mac = parts[3]
                if ip.startswith(AP_NET):
                    devices[mac] = ip
    except:
        pass
    return devices


def scan_subnet():
    """ARP scan the subnet for active devices."""
    devices = {}
    from scapy.all import ARP, Ether, srp
    try:
        arp = ARP(pdst=f"{AP_NET}.0/24")
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = ether / arp
        answered = srp(packet, timeout=2, iface="ap0", verbose=False)[0]
        for sent, recv in answered:
            devices[recv.hwsrc] = recv.psrc
    except:
        pass
    return devices


def monitor_devices(interval=2):
    """Continuously monitor for new devices on the AP."""
    seen_devices = {}
    known_devices = {}
    
    # Load known devices cache
    if os.path.exists(KNOWN_DEVICES_FILE):
        try:
            with open(KNOWN_DEVICES_FILE, "r") as f:
                known_devices = json.load(f)
        except:
            pass
    
    print(f"\n{'='*65}")
    print(f"{'[*] MONITORING FOR CONNECTED DEVICES...':^65}")
    print(f"{'[*] Press Ctrl+C to stop hotspot':^65}")
    print(f"{'='*65}\n")
    
    try:
        while True:
            # Get current MACs on the AP network
            current_arp = scan_arp()
            current_scan = scan_subnet() if not current_arp else {}
            
            # Merge: ARP file first, live scan as fallback
            all_current = {**current_scan, **current_arp}
            
            for mac, ip in all_current.items():
                if mac not in seen_devices and mac != "00:00:00:00:00:00":
                    # NEW DEVICE DETECTED!
                    info = get_device_info(ip, mac)
                    seen_devices[mac] = info
                    known_devices[mac] = info
                    
                    # Save to known devices
                    try:
                        with open(KNOWN_DEVICES_FILE, "w") as f:
                            json.dump(known_devices, f, indent=2)
                    except:
                        pass
                    
                    # Print alert
                    print(f"\n{'!'*60}")
                    print(f"  [NEW DEVICE CONNECTED]")
                    print(f"  Time:     {info['first_seen']}")
                    print(f"  IP:       {info['ip']}")
                    print(f"  MAC:      {info['mac']}")
                    print(f"  Vendor:   {info['vendor']}")
                    print(f"  Hostname: {info['hostname']}")
                    
                    # Try to get additional device info
                    # Check if device has ports open
                    ret, out, err = run_cmd(f"nmap -sn {ip} 2>/dev/null | grep -E 'Host is up|MAC'")
                    if out:
                        print(f"  Scanning:  {out[:60]}")
                    
                    print(f"{'!'*60}\n")
                
                elif mac in seen_devices:
                    # Update last seen
                    seen_devices[mac]["last_seen"] = datetime.now().strftime("%H:%M:%S")
            
            # Check for disconnected devices
            for mac in list(seen_devices.keys()):
                if mac not in all_current:
                    info = seen_devices[mac]
                    print(f"  [-] Device DISCONNECTED: {info['ip']} ({info['vendor']} - {info['mac']})")
                    del seen_devices[mac]
            
            # Show summary
            if seen_devices:
                print(f"\r  [ACTIVE: {len(seen_devices)} device(s)]   Last check: {datetime.now().strftime('%H:%M:%S')}", end="")
                sys.stdout.flush()
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n[*] Monitoring stopped.")


# ============================================================
# MAIN
# ============================================================

def main():
    print(BANNER)
    print(f"{'='*60}")
    print(f"{'Authorized Security Assessment Tool':^60}")
    print(f"{'Use only on systems you own or have permission to test.':^60}")
    print(f"{'='*60}\n")
    
    # Check root
    if not check_root():
        print("[!] Root access required. Run with:")
        print("    $ tsu")
        print("    $ python3 pineapple.py")
        sys.exit(1)
    
    # Check dependencies
    missing = check_deps()
    if missing:
        print("[!] Missing dependencies:")
        for dep, cmd in missing:
            print(f"    - {dep}  ->  {cmd}")
        sys.exit(1)
    
    # Get SSID
    ssid = input("[?] Enter hotspot SSID (default: 'Pineapple_AP'): ").strip()
    if not ssid:
        ssid = "Pineapple_AP"
    
    print(f"\n[*] Setting up hotspot '{ssid}'...")
    
    try:
        # Step 1: Create virtual AP interface
        print("[*] Creating virtual AP interface (ap0)...")
        run_cmd(f"iw dev {AP_IFACE} interface add ap0 type __ap")
        time.sleep(0.5)
        
        # Step 2: Configure and bring up ap0
        interface_up("ap0", AP_IP)
        
        # Step 3: Generate configs
        generate_hostapd_conf(ssid)
        generate_dnsmasq_conf()
        
        # Step 4: Enable IP forwarding (optional, for internet sharing)
        run_cmd("echo 1 > /proc/sys/net/ipv4/ip_forward")
        
        # Step 5: Start hotspot
        proc_h = start_hotspot()
        time.sleep(2)
        
        print(f"\n[+] Hotspot is LIVE!")
        print(f"    SSID:     {ssid}")
        print(f"    Security: OPEN (no password)")
        print(f"    IP Range: {AP_NET}.2 - {AP_NET}.100")
        print(f"    Gateway:  {AP_IP}")
        print(f"    Channel:  {AP_CHANNEL}")
        
        # Step 6: Monitor for devices
        monitor_devices()
        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\n[!] Error: {e}")
    finally:
        stop_hotspot() if 'proc_h' in locals() else None
        print("\n[+] Hotspot terminated. Goodbye.")


if __name__ == "__main__":
    main()
