import os
import time
import subprocess

ip = input("Enter IP address: ").strip()

while True:
    os.system("clear")

    print("========================================")
    print("          IP CALCULATOR LOOP")
    print("========================================")
    print(f"IP: {ip}")
    print()

    try:
        result = subprocess.run(
            ["ipcalc", ip],
            capture_output=True,
            text=True
        )

        print(result.stdout)

        if result.stderr:
            print("Error:", result.stderr)

    except FileNotFoundError:
        print("ipcalc is not installed.")
        print("Install it with: sudo apt install ipcalc")
        break

    print()
    print("Refreshing in 2 seconds...")

    time.sleep(2)
