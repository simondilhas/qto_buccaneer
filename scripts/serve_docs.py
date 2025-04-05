import http.server
import socketserver
import os

PORT = 8000

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="docs", **kwargs)

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving docs at http://localhost:{PORT}")
    httpd.serve_forever() 