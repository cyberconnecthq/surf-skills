#!/usr/bin/env python3
"""Local OAuth browser helper for surf-session login.

Starts a temporary HTTP server, opens Google Sign-In in the browser,
captures the ID token, and prints it to stdout as JSON.
"""

import http.server
import json
import socket
import sys
import threading
import webbrowser

GOOGLE_CLIENT_ID = "924320607654-7i39jp1damhqfa0ppf6evmt6jg9hjv20.apps.googleusercontent.com"
TIMEOUT = 120  # seconds

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
  <title>Surf - Sign in with Google</title>
  <script src="https://accounts.google.com/gsi/client" async></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
      display: flex; justify-content: center; align-items: center;
      min-height: 100vh; background: #0a0a0a; color: #e0e0e0;
    }
    .container { text-align: center; padding: 2rem; }
    h1 { font-size: 1.5rem; margin-bottom: 0.5rem; color: #fff; }
    .subtitle { color: #888; margin-bottom: 2rem; font-size: 0.95rem; }
    .signin-wrap { display: flex; justify-content: center; margin-bottom: 1.5rem; }
    #status { margin-top: 1rem; font-size: 0.9rem; transition: opacity 0.3s; }
    .success { color: #4CAF50; }
    .error { color: #f44336; }
    .pending { color: #888; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Surf Core</h1>
    <p class="subtitle">Sign in with Google to continue</p>
    <div class="signin-wrap">
      <div id="g_id_onload"
           data-client_id="__CLIENT_ID__"
           data-callback="onSignIn"
           data-auto_prompt="false">
      </div>
      <div class="g_id_signin"
           data-type="standard"
           data-size="large"
           data-theme="filled_black"
           data-text="sign_in_with"
           data-shape="rectangular"
           data-logo_alignment="left">
      </div>
    </div>
    <div id="status"></div>
  </div>
  <script>
    function onSignIn(response) {
      var el = document.getElementById('status');
      el.style.display = 'block';
      el.className = 'pending';
      el.textContent = 'Signing in...';
      fetch('/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential: response.credential })
      }).then(function(r) { return r.json(); })
        .then(function(data) {
          if (data.status === 'ok') {
            el.className = 'success';
            el.textContent = 'Done! This tab will close...';
            document.querySelector('.g_id_signin').style.display = 'none';
            setTimeout(function() { window.close(); }, 500);
          } else {
            el.className = 'error';
            el.textContent = 'Failed: ' + (data.error || 'Unknown error');
          }
        }).catch(function(err) {
          el.className = 'error';
          el.textContent = 'Error: ' + err.message;
        });
    }
  </script>
</body>
</html>""".replace("__CLIENT_ID__", GOOGLE_CLIENT_ID)

credential_result = None


class OAuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/login"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global credential_result
        if self.path == "/callback":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            credential = body.get("credential", "")
            if credential:
                credential_result = credential
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode())
                # Shut down server after sending response
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"status": "error", "error": "No credential"}).encode()
                )
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress HTTP request logs


PORT = 3000


def main():
    port = PORT
    server = http.server.HTTPServer(("localhost", port), OAuthHandler)

    # Timeout: auto-shutdown if user doesn't sign in
    def timeout_shutdown():
        import time

        time.sleep(TIMEOUT)
        if credential_result is None:
            server.shutdown()

    threading.Thread(target=timeout_shutdown, daemon=True).start()

    url = f"http://localhost:{port}/"
    webbrowser.open(url)
    server.serve_forever()

    if credential_result:
        print(json.dumps({"credential": credential_result}))
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
