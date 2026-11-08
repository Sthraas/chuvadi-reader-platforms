"""Minimal stand-in for Sangam's discovery/authorize endpoints (Web Test chat; test tooling only).
python3 sangam_stub.py <port> [--delay <seconds>] [--bad-json] [--wrong-issuer]
Serves /.well-known/openid-configuration, /.well-known/jwks and an /authorize page that shows the
query it received (so a test can read login_hint, PKCE and state). Never shipped."""
import json, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

port = int(sys.argv[1])
delay = float(sys.argv[sys.argv.index("--delay") + 1]) if "--delay" in sys.argv else 0
iss = f"http://127.0.0.1:{port}/"

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, body, ctype="application/json"):
        b = body.encode(); self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        time.sleep(delay)
        u = urlparse(self.path)
        if u.path == "/.well-known/openid-configuration":
            if "--bad-json" in sys.argv: return self.send(200, "{not json")
            d = {"issuer": "http://evil.example/" if "--wrong-issuer" in sys.argv else iss,
                 "authorization_endpoint": iss + "connect/authorize", "token_endpoint": iss + "connect/token",
                 "jwks_uri": iss + ".well-known/jwks", "end_session_endpoint": iss + "connect/endsession",
                 "response_types_supported": ["code"], "code_challenge_methods_supported": ["S256"],
                 "id_token_signing_alg_values_supported": ["ES256", "RS256"],
                 "authorization_response_iss_parameter_supported": True,
                 "backchannel_logout_supported": True, "backchannel_logout_session_supported": True}
            return self.send(200, json.dumps(d))
        if u.path == "/.well-known/jwks": return self.send(200, json.dumps({"keys": []}))
        if u.path == "/connect/authorize":
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            return self.send(200, "<html><body><h1>Stub Sangam authorize</h1><pre id=q>" + json.dumps(q, indent=1)
                             .replace("<", "&lt;") + "</pre></body></html>", "text/html")
        if u.path == "/connect/endsession": return self.send(200, "<h1>Stub end session</h1>", "text/html")
        self.send(404, "{}")

ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
