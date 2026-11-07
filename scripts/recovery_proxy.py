"""A temporary local API fault gate; only registered disposable mutations can fail."""

from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import socket
from threading import Thread,Lock
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from urllib.parse import urlsplit


class FaultGate:
    def __init__(self,address,checks):
        self.checks=checks;self.rules=[];self.lock=Lock();self.events=[]
        gate=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):self.forward()
            def do_POST(self):self.forward()
            def do_PUT(self):self.forward()
            def do_DELETE(self):self.forward()
            def forward(self):
                length=int(self.headers.get('Content-Length','0'));body=self.rfile.read(length) if length else None
                data=None
                if body and 'json' in self.headers.get('Content-Type',''):
                    data=json.loads(body)
                try:gate.checks.scope.check(self.command,self.path,data)
                except ValueError:
                    self.send_error(403,'Outside the recovery test scope');return
                rule=None
                with gate.lock:
                    for r in gate.rules:
                        if r['method']==self.command and r['path']==urlsplit(self.path).path and r['remaining']:
                            r['remaining']-=1;rule=r.copy();break
                if rule and rule['mode']=='before':
                    payload=b'{"detail":"Injected temporary failure before write"}'
                    self.send_response(503);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
                    gate.events.append({'method':self.command,'path':self.path,'fault':'before','forwarded':False});return
                headers={k:v for k,v in self.headers.items() if k.lower() not in {'host','connection','content-length'}}
                try:response=urlopen(Request('http://127.0.0.1:18001'+self.path,data=body,headers=headers,method=self.command),timeout=30)
                except HTTPError as error:response=error
                with response:status=response.status;payload=response.read();response_headers=response.headers
                gate.events.append({'method':self.command,'path':urlsplit(self.path).path,'status':status,'fault':rule['mode'] if rule else None,'forwarded':True})
                if rule and rule['mode']=='after':
                    self.close_connection=True
                    try:self.connection.shutdown(socket.SHUT_RDWR)
                    except OSError:pass
                    self.connection.close();return
                self.send_response(status)
                for k,v in response_headers.items():
                    if k.lower() not in {'connection','transfer-encoding','content-length'}:self.send_header(k,v)
                self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
        self.server=ThreadingHTTPServer(address,Handler)
        self.thread=Thread(target=self.server.serve_forever,daemon=True)

    def start(self):self.thread.start()
    def arm(self,path,mode,method='POST',count=1):
        self.checks.scope.check(method,path,[] if path.endswith('/metadata') else {})
        if not any(s in path for s in self.checks.scope.samples|self.checks.scope.groups):raise ValueError('Fault targets must be owned disposable objects')
        with self.lock:self.rules.append({'path':path,'mode':mode,'method':method,'remaining':count})
    def stop(self):self.server.shutdown();self.server.server_close()
