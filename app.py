"""
Traffic Signal System — Python HTTP Server Backend
Run: python server.py
Opens at: http://localhost:8000
"""

import json
import os
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# ─────────────────────── Simulation logic ───────────────────────

TIME_PER_VEHICLE   = 2   # seconds of green per vehicle
MIN_GREEN          = 5   # minimum green duration
MAX_GREEN          = 60  # maximum green duration
AMB_PRIORITY_TIME  = 10  # base green time when ambulance present
YELLOW_TIME        = 2   # yellow light duration (informational)

ROADS = ["North", "South", "East", "West"]

# Simulation history (in-memory list)
history: list[dict] = []


def calculate_duration(vehicles: int, ambulances: int) -> int:
    """Return the green-light duration in seconds for a road."""
    if ambulances > 0:
        return max(AMB_PRIORITY_TIME, vehicles * TIME_PER_VEHICLE)
    base = vehicles * TIME_PER_VEHICLE
    return min(max(base, MIN_GREEN), MAX_GREEN)


def build_simulation_plan(road_data: list[dict]) -> list[dict]:
    """
    Given a list of road input dicts, return an ordered plan.
    Roads with ambulances go first; then by vehicle count descending.
    Empty roads are appended at the end and marked as skipped.
    """
    active = [r for r in road_data if r["vehicles"] > 0 or r["ambulances"] > 0]
    empty  = [r for r in road_data if r["vehicles"] == 0 and r["ambulances"] == 0]

    active.sort(key=lambda x: (x["ambulances"] > 0, x["vehicles"]), reverse=True)

    plan = []
    for rd in active:
        dur = calculate_duration(rd["vehicles"], rd["ambulances"])
        plan.append({
            "road":       rd["road"],
            "vehicles":   rd["vehicles"],
            "ambulances": rd["ambulances"],
            "duration":   dur,
            "yellow":     YELLOW_TIME,
            "skipped":    False,
            "emergency":  rd["ambulances"] > 0,
        })
    for rd in empty:
        plan.append({
            "road":       rd["road"],
            "vehicles":   0,
            "ambulances": 0,
            "duration":   0,
            "yellow":     0,
            "skipped":    True,
            "emergency":  False,
        })
    return plan


# ─────────────────────── HTTP Handler ───────────────────────────

STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
MIME = {
    ".html": "text/html; charset=utf-8",
    ".css":  "text/css",
    ".js":   "application/javascript",
    ".ico":  "image/x-icon",
    ".png":  "image/png",
}


class TSSHandler(BaseHTTPRequestHandler):

    # ── helpers ──────────────────────────────────────────────────

    def _json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _err(self, msg: str, status: int = 400):
        self._json({"error": msg}, status)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return {}

    def _static(self, path: str):
        if path in ("/", ""):
            path = "/index.html"
        file_path = os.path.normpath(os.path.join(STATIC_DIR, path.lstrip("/")))
        if not file_path.startswith(STATIC_DIR):
            self.send_response(403); self.end_headers(); return
        if not os.path.isfile(file_path):
            self.send_response(404); self.end_headers()
            self.wfile.write(b"404 Not Found"); return
        ext  = os.path.splitext(file_path)[1]
        mime = MIME.get(ext, "application/octet-stream")
        with open(file_path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ── routing ──────────────────────────────────────────────────

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/simulate/config":
            # Return simulation constants so the frontend can display them
            self._json({
                "roads":            ROADS,
                "time_per_vehicle": TIME_PER_VEHICLE,
                "min_green":        MIN_GREEN,
                "max_green":        MAX_GREEN,
                "amb_priority_time": AMB_PRIORITY_TIME,
                "yellow_time":      YELLOW_TIME,
            })

        elif path == "/api/history":
            self._json({"history": list(reversed(history)), "count": len(history)})

        else:
            self._static(path)

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/simulate":
            data = self._body()
            roads_input = data.get("roads", [])

            # Validate
            if not isinstance(roads_input, list) or len(roads_input) != 4:
                self._err("Provide exactly 4 road entries.")
                return

            validated = []
            for entry in roads_input:
                road = str(entry.get("road", "")).strip()
                if road not in ROADS:
                    self._err(f"Unknown road: {road}"); return
                try:
                    v = int(entry.get("vehicles",  0)); assert v >= 0
                    a = int(entry.get("ambulances", 0)); assert a >= 0
                except (TypeError, ValueError, AssertionError):
                    self._err("vehicles and ambulances must be non-negative integers.")
                    return
                validated.append({"road": road, "vehicles": v, "ambulances": a})

            plan = build_simulation_plan(validated)

            # Save to history
            sim_id = str(uuid.uuid4())[:8]
            record = {
                "id":        sim_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "inputs":    validated,
                "plan":      plan,
                "total_duration": sum(
                    p["duration"] + p["yellow"]
                    for p in plan if not p["skipped"]
                ),
            }
            history.append(record)
            if len(history) > 50:          # keep last 50 sims
                history.pop(0)

            self._json({"simulation": record}, 201)

        else:
            self._err("Not found", 404)

    def log_message(self, fmt, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {fmt % args}")


# ─────────────────────── Entry point ────────────────────────────

if __name__ == "__main__":
    HOST, PORT = "localhost", 8000
    httpd = HTTPServer((HOST, PORT), TSSHandler)
    print(f"""
╔══════════════════════════════════════════════╗
║   🚦  Traffic Signal System — Server         ║
║   http://{HOST}:{PORT}                        ║
║   Press Ctrl+C to stop                       ║
╚══════════════════════════════════════════════╝
""")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] Stopped.")
