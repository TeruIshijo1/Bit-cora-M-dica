import ctypes
from ctypes import wintypes
import time
import os

_winbio = ctypes.windll.winbio
_winbio.WinBioOpenSession.argtypes = [
    ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_uint32), ctypes.c_size_t, ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_uint32)
]

def log(msg):
    with open("C:\\test_wbf.log", "a") as f:
        f.write(msg + "\n")

def run():
    log("Iniciando prueba SYSTEM...")
    handle = ctypes.c_uint32(0)
    hr = _winbio.WinBioOpenSession(8, 1, 0, None, 0, None, ctypes.byref(handle))
    log(f"OpenSession HR: 0x{hr & 0xFFFFFFFF:08X}")
    if hr != 0:
        return
        
    unit_id = wintypes.DWORD(0)
    log("Esperando dedo...")
    
    hr2 = _winbio.WinBioLocateSensor(handle, ctypes.byref(unit_id))
    log(f"LocateSensor HR: 0x{hr2 & 0xFFFFFFFF:08X}, Unit ID: {unit_id.value}")
    
    _winbio.WinBioCloseSession(handle)
    log("Prueba terminada.")

if __name__ == "__main__":
    run()
