#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import requests

HOST = "127.0.0.1"
PORT = 8000

class TestSite(BaseHTTPRequestHandler):
    def do_GET(self):
        page = """
        <html>
        <head><title>Test Site</title></head>
        <body>
            <h1>Local Test Website</h1>
            <p>Running for performance testing.</p>
        </body>
        </html>
        """

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(page.encode())

def start_server():
    server = HTTPServer((HOST, PORT), TestSite)
    print(f"[+] Website running at http://{HOST}:{PORT}")
    server.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

time.sleep(1)

print("\nMonitoring response time...\n")

while True:
    try:
        start = time.perf_counter()
        r = requests.get(f"http://{HOST}:{PORT}", timeout=5)
        latency = (time.perf_counter() - start) * 1000

        print(
            f"Status: {r.status_code} | "
            f"Response Time: {latency:.2f} ms"
        )

    except Exception as e:
        print("Error:", e)

    time.sleep(2)
