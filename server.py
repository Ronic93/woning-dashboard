import http.server,subprocess,os,json,threading
D=os.path.dirname(os.path.abspath(__file__)); os.chdir(D); lock=threading.Lock()
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self): self.send_header('Cache-Control','no-store'); super().end_headers()
    def do_POST(self):
        if self.path!='/api/refresh': return self.send_error(404)
        if not lock.acquire(blocking=False): r={"ok":False,"msg":"Refresh loopt al"}
        else:
            try: p=subprocess.run(["python3","refresh.py"],capture_output=True,text=True,timeout=900); r={"ok":p.returncode==0,"msg":(p.stdout+p.stderr)[-1500:]}
            finally: lock.release()
        b=json.dumps(r).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(b)
http.server.ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT',8420))),H).serve_forever()
