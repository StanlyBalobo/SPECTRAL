import random
import time
import os

def random_ip():
    return ".".join(str(random.randint(1, 254)) for _ in range(4))

def random_port():
    return random.randint(1000, 65535)

def banner():
    print(r"""
   _____                 _             _
  / ____|               | |           | |
 | (___  _ __   ___  ___| |_ _ __ __ _| |
  \___ \| '_ \ / _ \/ __| __| '__/ _` | |
  ____) | |_) |  __/ (__| |_| | | (_| | |
 |_____/| .__/ \___|\___|\__|_|  \__,_|_|
        | |
        |_|

        Spectral v1.0
   CCTV Simulation Terminal
""")

os.system("cls" if os.name == "nt" else "clear")
banner()

print("[1] Begin Scan")
print("[0] Exit")

choice = input("\nSelect: ")

if choice == "0":
    print("Exiting Spectral...")
    exit()

if choice == "1":
    print("\n\033[91m[!] Spectral Scanner Started\033[0m")
    print("\033[91mPress Ctrl+C to stop.\033[0m\n")

    try:
        while True:
            ip = random_ip()
            port = random_port()

            print(f"\033[91mhttps://{ip}:{port}\033[0m")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nScanner stopped by user.")
