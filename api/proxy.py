"""
Vercel serverless relay for the official SSS calculate-planner API.

Route: POST /api/proxy   (application/x-www-form-urlencoded)
Fields: age, monthlyIncome, desiredPension, volPenBoostContri

The browser posts the official payload to this same-origin function; the
function forwards it server-to-server to the official SSS endpoint and
returns the official JSON verbatim.  Server-to-server requests are not
subject to browser CORS - which is why this exists: member.sss.gov.ph
sends no Access-Control-Allow-Origin header, so a page hosted on
vercel.app could never read the response directly.

Python standard library only - no requirements.txt needed.
Vercel invokes the `handler` class below for every /api/proxy request.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

PLANNER_URL = "https://member.sss.gov.ph/member/pbl/pencalc/calculate-planner"
PLANNER_FIELDS = ("age", "monthlyIncome", "desiredPension", "volPenBoostContri")
UPSTREAM_TIMEOUT = 9  # keep below Vercel Hobby's 10s function limit

# Browser-like headers, same as the official pencalc.js request
_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "*/*",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Origin": "https://member.sss.gov.ph",
    "Referer": "https://member.sss.gov.ph/member/pbl/pencalc/",
}


def _sanitize(raw_body: bytes) -> bytes:
    """Keep only the four planner fields (names/order as in pencalc.js)."""
    parsed = urllib.parse.parse_qs(
        raw_body.decode("utf-8", "replace"), keep_blank_values=True
    )
    clean = [
        (field, (parsed.get(field) or [""])[0].strip())
        for field in PLANNER_FIELDS
    ]
    return urllib.parse.urlencode(clean).encode("ascii")


def _call_planner(form_body: bytes):
    """Forward the form body to the official SSS endpoint (server-to-server)."""
    request = urllib.request.Request(
        PLANNER_URL, data=form_body, headers=_HEADERS, method="POST"
    )
    with urllib.request.urlopen(request, timeout=UPSTREAM_TIMEOUT) as response:
        return response.status, response.read()


class handler(BaseHTTPRequestHandler):
    """Vercel Python function entry point for POST /api/proxy."""

    def _send_json(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        # CORS preflight - not needed same-origin, harmless if page is opened
        # from another host; keeps the function usable from anywhere.
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            form_body = _sanitize(raw)
        except Exception as exc:
            self._send_json(400, {"errorNum": -1, "error": "bad request: %s" % exc})
            return

        try:
            status, upstream = _call_planner(form_body)
        except urllib.error.HTTPError as exc:
            detail = ""
            if exc.fp:
                detail = exc.read()[:500].decode("utf-8", "replace")
            self._send_json(
                502,
                {
                    "errorNum": -2,
                    "error": "SSS replied HTTP %d" % exc.code,
                    "detail": detail,
                },
            )
            return
        except Exception as exc:  # timeout / DNS / TLS
            self._send_json(502, {"errorNum": -2, "error": "SSS unreachable: %s" % exc})
            return

        try:
            payload = json.loads(upstream.decode("utf-8", "replace"))
        except Exception:
            self._send_json(502, {"errorNum": -2, "error": "SSS returned non-JSON body"})
            return

        # Log outcome only (no payload) - age/income never hit the logs.
        print("planner: http=%s errorNum=%s" % (status, payload.get("errorNum")))
        self._send_json(status, payload)  # official JSON passthrough
