#!/usr/bin/env python3

import os
import subprocess
import time

# ANSI Colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
RESET = "\033[0m"
BOLD = "\033[1m"

def clear():
    os.system("clear")

def banner():
    print(f"""{CYAN}{BOLD}
████████╗██████╗  █████╗  ██████╗███████╗
╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██╔════╝
   ██║   ██████╔╝███████║██║     █████╗
   ██║   ██╔══██╗██╔══██║██║     ██╔══╝
   ██║   ██║  ██║██║  ██║╚██████╗███████╗
   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚══════╝
{RESET}""")

    print(f"{MAGENTA}{'='*50}{RESET}")
    print(f"{GREEN}{BOLD}        TRACE ROUTE LOOP TOOL{RESET}")
    print(f"{MAGENTA}{'='*50}{RESET}")
    print(f"{WHITE}Target : {YELLOW}google.com{RESET}")
    print()

clear()
banner()

input(f"{CYAN}[>] Press {GREEN}ENTER{CYAN} to start...{RESET}")

count = 1

try:
    while True:
        print(f"\n{GREEN}[+] Trace #{count}{RESET}")
        print(f"{YELLOW}{'-'*50}{RESET}")

        subprocess.run([
            "traceroute",
            "-m", "15",
            "-w", "1",
            "google.com"
        ])

        print(f"{GREEN}[✓] Trace #{count} complete.{RESET}")
        print(f"{CYAN}Restarting in 2 seconds... (Press Ctrl+C to stop){RESET}")

        count += 1
        time.sleep(2)

except KeyboardInterrupt:
    print(f"\n\n{RED}[!] Program stopped by user (Ctrl+C).{RESET}")
