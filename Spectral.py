#!/usr/bin/env python3

import os
import subprocess
import time

# ANSI Colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
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
    print(f"{GREEN}{BOLD}           TRACE ROUTE TOOL{RESET}")
    print(f"{MAGENTA}{'='*50}{RESET}")
    print(f"{WHITE}Target : {YELLOW}google.com{RESET}")
    print()

clear()
banner()

input(f"{CYAN}[>] Press {GREEN}ENTER{CYAN} to start tracing...{RESET}")

print()
print(f"{GREEN}[+] Initializing...{RESET}")
time.sleep(0.5)

print(f"{GREEN}[+] Resolving Host...{RESET}")
time.sleep(0.5)

print(f"{GREEN}[+] Starting Trace...{RESET}")
print()

try:
    subprocess.run(
        [
            "traceroute",
            "-m", "15",     # Max hops
            "-w", "1",      # 1 second timeout per hop
            "google.com"
        ],
        timeout=20
    )

except FileNotFoundError:
    print(f"{RED}[!] traceroute is not installed!{RESET}")
    print(f"{YELLOW}Run:{RESET} pkg install traceroute")

except subprocess.TimeoutExpired:
    print()
    print(f"{RED}[!] Trace timed out after 20 seconds.{RESET}")

except KeyboardInterrupt:
    print()
    print(f"{YELLOW}[!] Trace cancelled by user.{RESET}")

except Exception as e:
    print(f"{RED}[!] Error: {e}{RESET}")

print()
print(f"{GREEN}[✓] Finished!{RESET}")
input(f"{CYAN}Press {GREEN}ENTER{CYAN} to exit...{RESET}")
