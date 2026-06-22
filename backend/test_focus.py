import ctypes
from ctypes import wintypes
import tkinter as tk
import threading
import time

_winbio = ctypes.windll.winbio

def capture_fingerprint(root):
    handle = ctypes.c_uint32(0)
    hr = _winbio.WinBioOpenSession(8, 1, 0, None, 0, None, ctypes.byref(handle))
    if hr != 0:
        print(f"OpenSession Error: 0x{hr:08X}")
        root.quit()
        return

    print("Coloca tu dedo en el lector AHORA...")
    unit_id = wintypes.DWORD(0)
    hr2 = _winbio.WinBioLocateSensor(handle, ctypes.byref(unit_id))
    print(f"LocateSensor: 0x{hr2 & 0xFFFFFFFF:08X}, Unit: {unit_id.value}")

    _winbio.WinBioCloseSession(handle)
    root.quit()

def main():
    root = tk.Tk()
    root.title("Lector")
    root.geometry("200x100")
    root.attributes('-topmost', True)
    
    # Steal focus
    root.focus_force()
    
    lbl = tk.Label(root, text="Por favor ponga su dedo...")
    lbl.pack(pady=20)
    
    t = threading.Thread(target=capture_fingerprint, args=(root,))
    t.daemon = True
    t.start()
    
    root.mainloop()

if __name__ == "__main__":
    main()
