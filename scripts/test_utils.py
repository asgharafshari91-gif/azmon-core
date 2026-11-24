import json,socket,time

def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]

def wait(fn,timeout=30):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        try:
            if fn():return
        except (RuntimeError,OSError,json.JSONDecodeError):pass
        time.sleep(.1)
    raise RuntimeError('Timed out waiting for node state')
