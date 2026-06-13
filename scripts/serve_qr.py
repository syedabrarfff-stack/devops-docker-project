#!/usr/bin/env python3
import json, os, urllib.request, time

os.system("pkill -f 'http.server 9090' 2>/dev/null; sleep 1")

req = urllib.request.Request("http://localhost:8080/instance/connect/jarvis-main")
req.add_header("apikey", "jarvis-master-key")
try:
    r = urllib.request.urlopen(req, timeout=10)
    d = json.loads(r.read())
    b64 = d.get("base64", "")
    code = d.get("code", "")
    print("CODE:", code[:80])
    if b64:
        html = (
            "<html><body style='background:#fff;text-align:center'>"
            "<h2 style='color:red'>SCAN WITH WHATSAPP NOW — expires ~20s</h2>"
            "<img style='width:450px' src='" + b64 + "'>"
            "<p style='font-size:12px'>Refresh page to get a new code</p>"
            "</body></html>"
        )
        with open("/tmp/qr.html", "w") as f:
            f.write(html)
        print("QR_SAVED: /tmp/qr.html")
    else:
        print("NO_BASE64")
        print(json.dumps(d)[:400])
except Exception as e:
    print("ERROR:", e)

os.system("nohup python3 -m http.server 9090 --directory /tmp >/tmp/srv.log 2>&1 &")
time.sleep(1)
print("SERVER_UP: http://18.61.35.255:9090/qr.html")
print("OPEN THAT URL NOW AND SCAN WITHIN 20 SECONDS")
