from pathlib import Path
import subprocess
import sys
import time
import json
import urllib.request
import urllib.error
import socket

ROOT=Path(__file__).resolve().parents[2]
LOG=ROOT/'.work'/'debug'/'server-startup.log'
OUT=ROOT/'.work'/'debug'/'server-http-check.json'
with socket.socket() as s:
    existing_server = s.connect_ex(('127.0.0.1',5000)) == 0
results=[]
with LOG.open('w',encoding='utf-8') as log:
    process=None if existing_server else subprocess.Popen([sys.executable,'app.py'],cwd=str(ROOT),stdout=log,stderr=subprocess.STDOUT)
    try:
        ready=existing_server
        deadline=time.monotonic()+40
        while not ready and time.monotonic()<deadline and process.poll() is None:
            try:
                with socket.create_connection(('127.0.0.1',5000),timeout=0.5):
                    ready=True
                    break
            except OSError:
                time.sleep(0.25)
        if not ready:
            print('startup_failed; detalles en .work/debug/server-startup.log')
            raise SystemExit(1)
        for path in ['/','/auth/login','/auth/register','/api/categories','/api/platform/manifest','/api/platform/health']:
            with urllib.request.urlopen('http://127.0.0.1:5000'+path,timeout=20) as response:
                response.read()
                results.append({'path':path,'status':response.status,'ok':response.status==200})
        for path in ['/api/ai/interpret','/api/platform/me/profile']:
            req=urllib.request.Request('http://127.0.0.1:5000'+path,data=b'{}',headers={'Content-Type':'application/json'},method='PATCH' if 'profile' in path else 'POST')
            try:
                response=urllib.request.urlopen(req,timeout=10)
                status=response.status
                data=json.loads(response.read())
            except urllib.error.HTTPError as error:
                status=error.code
                data=json.loads(error.read())
            results.append({'path':path,'status':status,'ok':status==400 and data.get('code')=='csrf_invalid'})
        OUT.write_text(json.dumps(results,indent=2),encoding='utf-8')
        print(json.dumps({'started_by_qa':not existing_server,'existing_server':existing_server,'http_checks':results},indent=2))
        raise SystemExit(0 if all(item['ok'] for item in results) else 1)
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
