# Kuzya Tray App — HTTP контроллер для Домовёнка Кузи
# Эндпоинты: /toggle, /shutdown(/off,/power_off), /state,
#            /get_volume, /set_volume?value=N, /volume_up?step=5, /volume_down?step=5,
#            /get_mute, /set_mute?value=0|1, /mute, /unmute, /toggle_mute
# Требуются: PySide6, comtypes, pycaw  (pip install PySide6 comtypes pycaw)

import sys, ctypes, threading, argparse, json, socket, subprocess, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from ctypes import wintypes

if sys.platform != "win32":
    raise SystemExit("Только Windows.")

# ---------- Toggle Media (низкоуровнево)
user32 = ctypes.WinDLL("user32", use_last_error=True)
if ctypes.sizeof(ctypes.c_void_p) == 8:
    ULONG_PTR = ctypes.c_ulonglong
else:
    ULONG_PTR = ctypes.c_ulong

VK_MEDIA_PLAY_PAUSE = 0xB3
SCAN_MEDIA_PLAY_PAUSE = 0x22
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP       = 0x0002
KEYEVENTF_SCANCODE    = 0x0008

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk",wintypes.WORD),("wScan",wintypes.WORD),("dwFlags",wintypes.DWORD),
                ("time",wintypes.DWORD),("dwExtraInfo",ULONG_PTR)]
class _UN(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]
class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _UN)]

user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ULONG_PTR]

def _send_vk(vk:int):
    arr = (INPUT*2)(
        INPUT(type=1, union=_UN(ki=KEYBDINPUT(vk,0,0,0,0))),
        INPUT(type=1, union=_UN(ki=KEYBDINPUT(vk,0,KEYEVENTF_KEYUP,0,0))),
    ); user32.SendInput(2, arr, ctypes.sizeof(INPUT))

def _send_scan(sc:int):
    arr = (INPUT*2)(
        INPUT(type=1, union=_UN(ki=KEYBDINPUT(0,sc,KEYEVENTF_SCANCODE|KEYEVENTF_EXTENDEDKEY,0,0))),
        INPUT(type=1, union=_UN(ki=KEYBDINPUT(0,sc,KEYEVENTF_SCANCODE|KEYEVENTF_EXTENDEDKEY|KEYEVENTF_KEYUP,0,0))),
    ); user32.SendInput(2, arr, ctypes.sizeof(INPUT))

def _keybd_event_vk(vk:int):
    user32.keybd_event(vk,0,0,0); user32.keybd_event(vk,0,KEYEVENTF_KEYUP,0)

def toggle_media_hard(mode="auto"):
    m = (mode or "auto").lower()
    if m=="vk": _send_vk(VK_MEDIA_PLAY_PAUSE)
    elif m=="scan": _send_scan(SCAN_MEDIA_PLAY_PAUSE)
    elif m=="keybd": _keybd_event_vk(VK_MEDIA_PLAY_PAUSE)
    else: _send_vk(VK_MEDIA_PLAY_PAUSE); _send_scan(SCAN_MEDIA_PLAY_PAUSE); _keybd_event_vk(VK_MEDIA_PLAY_PAUSE)

# ---------- CoreAudio через pycaw (надёжные сигнатуры)
PYCAW_OK, PYCAW_ERR, PYCAW_PATH = False, None, None
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    import pycaw as _pycaw_mod
    PYCAW_OK = True
    PYCAW_PATH = getattr(_pycaw_mod, "__file__", None)
except Exception as e:
    PYCAW_ERR = repr(e)

if PYCAW_OK:
    def _get_ep():
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))

    def vol_get()->int:
        ep = _get_ep()
        # pycaw прописывает errcheck и возвращает float без out-параметра
        f = ep.GetMasterVolumeLevelScalar()
        try:
            f = float(f)
        except Exception:
            # на редких билдах может вернуться c_float
            f = getattr(f, "value", 0.0)
        return int(round(max(0.0, min(1.0, f))*100))

    def vol_set(val:int)->int:
        v = max(0, min(100, int(val)))
        ep = _get_ep()
        ep.SetMasterVolumeLevelScalar(v/100.0, None)
        return v

    def vol_step(delta:int)->int:
        return vol_set(vol_get()+int(delta))

    def mute_get()->int:
        ep = _get_ep()
        m = ep.GetMute()
        try:
            m = int(m)
        except Exception:
            m = 1 if getattr(m, "value", 0) else 0
        return 1 if m else 0

    def mute_set(val01:int)->int:
        ep = _get_ep()
        v = 1 if int(val01) else 0
        ep.SetMute(v, None)
        return v

else:
    # Явно сообщаем, что нужна pycaw (так мы избегаем кривых vtable-описаний)
    def _no():
        raise RuntimeError(f"pycaw не доступна: {PYCAW_ERR}. Установите: pip install pycaw")
    def vol_get()->int: _no()
    def vol_set(val:int)->int: _no()
    def vol_step(delta:int)->int: _no()
    def mute_get()->int: _no()
    def mute_set(val01:int)->int: _no()

# ---------- Утилиты
def get_local_ip():
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(('8.8.8.8',80))
        ip=s.getsockname()[0]; s.close(); return ip
    except Exception: return '127.0.0.1'

def shutdown_now():
    try: subprocess.run(["shutdown","/s","/t","0"], check=False)
    except Exception as e: print("shutdown error:", e)

# ---------- HTTP
class Ctx:
    def __init__(self, token, toggle_mode): self.token=token; self.toggle_mode=toggle_mode

def _parse_json_body(h:BaseHTTPRequestHandler):
    try: L=int(h.headers.get('Content-Length','0'))
    except: L=0
    if L<=0: return None
    try: return json.loads(h.rfile.read(L).decode('utf-8',errors='ignore') or '{}')
    except: return None

_num_re = re.compile(r"-?\d+")
def _int_like(x, default=None):
    if x is None: return default
    if isinstance(x,(int,float)):
        try: return int(x)
        except: return default
    m=_num_re.search(str(x)); return int(m.group(0)) if m else default

def make_handler(ctx:Ctx):
    class H(BaseHTTPRequestHandler):
        server_version="KuzyaTray/1.5"
        def _send(self,code,payload):
            b=json.dumps(payload,ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Content-Length",str(len(b)))
            self.end_headers(); self.wfile.write(b)
        def log_message(self,*a,**k): return
        def _ok(self,**kv): self._send(200, {"ok":True, **kv})
        def _err(self,code,msg,**kv): self._send(code, {"ok":False,"error":msg,**kv})
        def _handle(self,method):
            p=urlparse(self.path); qs=parse_qs(p.query or '')
            body=_parse_json_body(self) if method=='POST' else None
            def num(name, default=None):
                if body and name in body:
                    v=_int_like(body.get(name)); 
                    if v is not None: return v
                if name in qs and qs[name]:
                    v=_int_like(qs[name][0]); 
                    if v is not None: return v
                return default
            try:
                if p.path=='/toggle':
                    toggle_media_hard(ctx.toggle_mode); return self._ok(action="toggle")
                if p.path in ('/shutdown','/off','/power_off'):
                    threading.Thread(target=shutdown_now,daemon=True).start(); return self._ok(action="shutdown")
                if p.path=='/state':
                    return self._ok(value=1, pycaw=PYCAW_PATH or PYCAW_ERR or "unknown")
                if p.path=='/get_volume':
                    return self._ok(value=vol_get())
                if p.path=='/set_volume':
                    v=num('value'); 
                    if v is None: return self._err(400,"missing_value")
                    return self._ok(value=vol_set(v))
                if p.path=='/volume_up':
                    st=abs(num('step',5)); return self._ok(action="volume_up", value=vol_step(st))
                if p.path=='/volume_down':
                    st=abs(num('step',5)); return self._ok(action="volume_down", value=vol_step(-st))
                if p.path=='/get_mute':
                    return self._ok(value=mute_get())
                if p.path=='/set_mute':
                    v=num('value'); 
                    if v is None: return self._err(400,"missing_value")
                    return self._ok(value=mute_set(1 if int(v) else 0))
                if p.path=='/mute':
                    return self._ok(value=mute_set(1))
                if p.path=='/unmute':
                    return self._ok(value=mute_set(0))
                if p.path=='/toggle_mute':
                    cur=mute_get(); return self._ok(value=mute_set(0 if cur else 1))
                if p.path in ('/',''):
                    return self._ok(endpoints=[
                        "/toggle","/shutdown","/off","/power_off","/state",
                        "/get_volume","/set_volume?value=0..100","/volume_up?step=5","/volume_down?step=5",
                        "/get_mute","/set_mute?value=0|1","/mute","/unmute","/toggle_mute"
                    ], pycaw=PYCAW_PATH or PYCAW_ERR or "unknown")
                return self._err(404,"not_found")
            except Exception as e:
                return self._err(500,"exception", detail=str(e))
        def do_GET(self): self._handle('GET')
        def do_POST(self): self._handle('POST')
    return H

class HttpThread(threading.Thread):
    def __init__(self, host, port, handler_factory):
        super().__init__(daemon=True); self.host=host; self.port=port; self.handler_factory=handler_factory; self.httpd=None
    def run(self):
        self.httpd=ThreadingHTTPServer((self.host,self.port), self.handler_factory)
        self.httpd.serve_forever(poll_interval=0.5)
    def stop(self):
        try: self.httpd and self.httpd.shutdown()
        except: pass

# ---------- Трей
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox, QStyle
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QTimer

def make_icon(app): 
    try: return app.style().standardIcon(QStyle.SP_MediaVolume)
    except: return QIcon()

def build_tray(app, server, port):
    tray=QSystemTrayIcon(make_icon(app)); tray.setToolTip("Kuzya Tray")
    m=QMenu()
    a=QAction("Toggle Play/Pause"); a.triggered.connect(lambda: toggle_media_hard("auto")); m.addAction(a)
    b=QAction("Выключить компьютер…")
    def _conf():
        if QMessageBox.question(None,"Выключение","Выключить сейчас?", QMessageBox.Yes|QMessageBox.No, QMessageBox.No)==QMessageBox.Yes:
            shutdown_now()
    b.triggered.connect(_conf); m.addAction(b)
    m.addSeparator()
    q=QAction("Выход"); q.triggered.connect(lambda: (server.stop(), app.quit())); m.addAction(q)
    tray.setContextMenu(m); tray.show()
    def welcome():
        ip=get_local_ip()
        msg = f"Слушаю на http://{ip}:{port}\n/toggle, /shutdown, /get_volume, /set_volume, /get_mute, /set_mute …"
        tray.showMessage("Kuzya Tray", msg, QSystemTrayIcon.Information, 8000)
    QTimer.singleShot(1200, welcome)
    return tray

# ---------- main
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=45583)
    ap.add_argument("--toggle-mode", choices=["auto","vk","scan","keybd","all"], default="auto")
    args=ap.parse_args()

    print("Python:", sys.executable)
    print("pycaw:", PYCAW_PATH or PYCAW_ERR)

    ctx=Ctx(token=None, toggle_mode=args.toggle_mode)
    handler=make_handler(ctx)
    srv=HttpThread(args.host, args.port, handler); srv.start()

    app=QApplication(sys.argv); tray=build_tray(app, srv, args.port)
    sys.exit(app.exec())

if __name__=="__main__":
    main()
