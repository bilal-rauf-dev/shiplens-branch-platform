"""Disposable CI proxy: emulate Render TLS for every browser/auditor request.

Never deploy this HTTP-only helper. Compose exposes it only on host loopback.
The upstream is fixed to the private seeded web service, not a request parameter.
"""

import http.client
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


class BrowserProxy(BaseHTTPRequestHandler):
    def forward(self):
        """Keep production redirects/cookies intact behind a trusted proxy."""
        upstream = http.client.HTTPConnection("web", 8000, timeout=65)
        try:
            if not self.path.startswith("/"):
                self.send_error(400)
                return
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            headers = {
                key: value
                for key, value in self.headers.items()
                if key.lower() not in HOP_HEADERS
                and key.lower() not in {"x-forwarded-proto", "x-forwarded-for"}
            }
            headers["X-Forwarded-Proto"] = "https"
            headers["X-Forwarded-For"] = self.client_address[0]
            upstream.request(self.command, self.path, body=body, headers=headers)
            response = upstream.getresponse()
            self.send_response_only(response.status)
            for key, value in response.getheaders():
                if key.lower() not in HOP_HEADERS:
                    self.send_header(key, value)
            self.send_header("Connection", "close")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(response.read())
        except (OSError, http.client.HTTPException, ValueError):
            self.send_error(502)
        finally:
            self.close_connection = True
            upstream.close()

    do_GET = forward
    do_HEAD = forward
    do_POST = forward

    def log_message(self, format, *args):
        """The upstream already records correlated access logs without URLs."""


if __name__ == "__main__":
    address = (os.environ.get("CI_PROXY_BIND", "127.0.0.1"), 8000)
    ThreadingHTTPServer(address, BrowserProxy).serve_forever()
