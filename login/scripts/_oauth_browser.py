#!/usr/bin/env python3
"""Local OAuth browser helper for surf-session login.

Starts a temporary HTTP server, opens Google Sign-In in a small popup window,
captures the ID token, and prints it to stdout as JSON.
"""

import http.server
import json
import os
import platform
import socket
import subprocess
import sys
import threading
import webbrowser

GOOGLE_CLIENT_ID = "924320607654-7i39jp1damhqfa0ppf6evmt6jg9hjv20.apps.googleusercontent.com"
TIMEOUT = 120  # seconds

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
  <title>Surf — Sign In</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://accounts.google.com/gsi/client" async></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
      display: flex; justify-content: center; align-items: center;
      min-height: 100vh;
      background: linear-gradient(145deg, #0a0a0f 0%, #0d1117 50%, #0a0f1a 100%);
      color: #e0e0e0;
      overflow: hidden;
    }
    .bg-glow {
      position: fixed; top: -40%; left: -20%; width: 140%; height: 140%;
      background: radial-gradient(ellipse at 30% 20%, rgba(56, 189, 248, 0.06) 0%, transparent 50%),
                  radial-gradient(ellipse at 70% 80%, rgba(139, 92, 246, 0.05) 0%, transparent 50%);
      pointer-events: none; z-index: 0;
    }
    .container {
      position: relative; z-index: 1;
      text-align: center; padding: 2.5rem 2rem;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 20px;
      backdrop-filter: blur(20px);
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
      min-width: 320px;
      animation: fadeUp 0.5s ease-out;
    }
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(16px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .logo {
      width: 56px; height: 56px; margin: 0 auto 1.2rem;
      background: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #a78bfa 100%);
      border-radius: 14px; display: flex; align-items: center; justify-content: center;
      box-shadow: 0 4px 16px rgba(56, 189, 248, 0.25);
    }
    .logo svg { width: 32px; height: 32px; }
    h1 {
      font-size: 1.35rem; font-weight: 600; margin-bottom: 0.35rem;
      color: #fff; letter-spacing: -0.01em;
    }
    .subtitle {
      color: rgba(255, 255, 255, 0.45); margin-bottom: 2rem;
      font-size: 0.88rem; font-weight: 400;
    }
    .signin-wrap {
      display: flex; justify-content: center; margin-bottom: 1rem;
      min-height: 44px;
    }
    #status {
      margin-top: 0.8rem; font-size: 0.85rem;
      transition: all 0.3s ease;
    }
    .success {
      color: #34d399;
      animation: pulse 0.5s ease;
    }
    .error { color: #f87171; }
    .pending { color: rgba(255, 255, 255, 0.5); }
    @keyframes pulse {
      0% { transform: scale(1); }
      50% { transform: scale(1.05); }
      100% { transform: scale(1); }
    }
    .footer {
      margin-top: 2rem; font-size: 0.75rem;
      color: rgba(255, 255, 255, 0.2);
    }
  </style>
</head>
<body>
  <div class="bg-glow"></div>
  <div class="container">
    <div class="logo"><svg width="32" height="32" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M14.6875 13.333C15.0977 13.333 15.4859 13.5196 15.7422 13.8398L17.8721 16.502C17.9009 16.538 17.9308 16.5721 17.9619 16.6035C18.3091 16.9542 18.7529 17.3405 18.7529 17.834C18.7528 18.3399 18.3428 18.75 17.8369 18.75H17.5713C17.2123 18.75 16.8727 18.5869 16.6484 18.3066L15.4678 16.8311C14.761 15.9479 13.3369 16.4478 13.3369 17.5791V18.6494C13.3369 18.7062 13.2882 18.75 13.2314 18.75H11.3584C10.7127 18.75 10.1016 18.4564 9.69824 17.9521L8.80176 16.8311C8.09497 15.9477 6.66993 16.4478 6.66992 17.5791V18.6494C6.66991 18.7062 6.62124 18.75 6.56445 18.75H4.69141C4.04589 18.75 3.43548 18.4562 3.03223 17.9521L2.13477 16.8311C1.77885 16.3862 1.25293 15.931 1.25293 15.3613V13.4395C1.253 13.3822 1.29729 13.3331 1.35449 13.333C1.7646 13.3332 2.15295 13.5196 2.40918 13.8398L4.53809 16.502C5.24478 17.3853 6.66962 16.886 6.66992 15.7549V14.6836C6.67018 13.9379 7.27483 13.3332 8.02051 13.333C8.43065 13.333 8.81884 13.5197 9.0752 13.8398L11.2051 16.502C11.9097 17.3827 13.3282 16.8887 13.3369 15.7646V14.6836C13.3372 13.9378 13.9417 13.3331 14.6875 13.333ZM14.6875 6.66699C15.0978 6.66702 15.4859 6.85347 15.7422 7.17383L17.8721 9.83594C18.2276 10.2801 18.7526 10.7339 18.7529 11.3027V13.2266C18.7528 13.2833 18.7091 13.333 18.6523 13.333C18.2421 13.3329 17.8539 13.1465 17.5977 12.8262L15.4678 10.1641C14.7609 9.28113 13.3369 9.78089 13.3369 10.9121V11.9824C13.3369 12.7282 12.7321 13.3328 11.9863 13.333C11.5761 13.3329 11.187 13.1465 10.9307 12.8262L8.80176 10.1641C8.09497 9.28072 6.66993 9.78076 6.66992 10.9121V11.9824C6.66992 12.7284 6.06525 13.3329 5.31934 13.333C4.90908 13.3329 4.52094 13.1465 4.26465 12.8262L2.13477 10.1641C1.7788 9.71925 1.25293 9.26403 1.25293 8.69434V6.77344C1.253 6.71621 1.29728 6.6671 1.35449 6.66699C1.76461 6.66714 2.15295 6.85359 2.40918 7.17383L4.53809 9.83594C5.24487 10.7193 6.66989 10.2192 6.66992 9.08789V8.01758C6.66992 7.27168 7.27467 6.66722 8.02051 6.66699C8.43082 6.66699 8.81885 6.85345 9.0752 7.17383L11.2051 9.83594C11.9097 10.7163 13.3279 10.2223 13.3369 9.09863V8.01758C13.3369 7.27161 13.9416 6.6671 14.6875 6.66699ZM2.43555 1.25C2.79488 1.25 3.13499 1.41367 3.35938 1.69434L4.53809 3.16895C5.24485 4.05241 6.66991 3.55228 6.66992 2.4209V1.35059C6.66993 1.29391 6.71874 1.25017 6.77539 1.25H8.64844C9.29394 1.25 9.90438 1.5438 10.3076 2.04785L11.2051 3.16895C11.9097 4.04967 13.3282 3.55564 13.3369 2.43164V1.35059C13.3369 1.29391 13.3857 1.25017 13.4424 1.25H15.3154C15.9609 1.25 16.5714 1.5438 16.9746 2.04785L17.8721 3.16895C18.2275 3.61314 18.7526 4.06689 18.7529 4.63574V6.56055C18.7528 6.61728 18.7091 6.66699 18.6523 6.66699C18.2421 6.66688 17.8539 6.4795 17.5977 6.15918L15.4678 3.49805C14.761 2.61474 13.3371 3.11388 13.3369 4.24512V5.31543C13.3369 6.06126 12.7321 6.66673 11.9863 6.66699C11.5761 6.66693 11.187 6.47955 10.9307 6.15918L8.80176 3.49805C8.095 2.61474 6.67006 3.11388 6.66992 4.24512V5.31543C6.66992 6.06137 6.06525 6.66691 5.31934 6.66699C4.90908 6.66693 4.52094 6.47955 4.26465 6.15918L2.13477 3.49805C2.10558 3.46158 2.07543 3.42725 2.04395 3.39551C1.6966 3.04528 1.25293 2.6583 1.25293 2.16504C1.25317 1.65963 1.66348 1.25 2.16895 1.25H2.43555Z" fill="white"/></svg></div>
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
           data-shape="pill"
           data-logo_alignment="left">
      </div>
    </div>
    <div id="status"></div>
    <div class="footer">Crypto Intelligence Platform</div>
  </div>
  <script>
    function onSignIn(response) {
      var el = document.getElementById('status');
      el.style.display = 'block';
      el.className = 'pending';
      el.textContent = 'Signing in…';
      fetch('/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential: response.credential })
      }).then(function(r) { return r.json(); })
        .then(function(data) {
          if (data.status === 'ok') {
            el.className = 'success';
            el.textContent = '✓ Signed in — closing…';
            document.querySelector('.g_id_signin').style.display = 'none';
            setTimeout(function() { window.close(); }, 800);
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


def open_popup(url, width=420, height=520):
    """Open URL in a small popup window. Falls back to default browser."""
    if platform.system() == "Darwin":
        # macOS: use AppleScript to open a small Chrome or Safari window
        for browser_script in [
            # Try Chrome first
            f'''
            tell application "Google Chrome"
                set w to make new window
                set bounds of w to {{200, 150, {200 + width}, {150 + height}}}
                set URL of active tab of w to "{url}"
                activate
            end tell
            ''',
            # Fall back to Safari
            f'''
            tell application "Safari"
                make new document with properties {{URL:"{url}"}}
                set bounds of front window to {{200, 150, {200 + width}, {150 + height}}}
                activate
            end tell
            ''',
        ]:
            try:
                subprocess.run(
                    ["osascript", "-e", browser_script],
                    capture_output=True, timeout=5,
                )
                return
            except Exception:
                continue
    # Fallback: default browser (full window)
    webbrowser.open(url)

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
    open_popup(url)
    server.serve_forever()

    if credential_result:
        print(json.dumps({"credential": credential_result}))
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
