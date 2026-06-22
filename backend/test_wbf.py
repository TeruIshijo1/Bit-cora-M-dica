import ctypes
from ctypes import wintypes

_winbio = ctypes.windll.winbio

_winbio.WinBioOpenSession.argtypes = [
    ctypes.c_uint32, # Factor
    ctypes.c_uint32, # PoolType
    ctypes.c_uint32, # Flags
    ctypes.POINTER(ctypes.c_uint32), # UnitArray
    ctypes.c_size_t, # UnitCount
    ctypes.c_void_p, # DatabaseId
    ctypes.POINTER(ctypes.c_uint32) # SessionHandle
]

def test_private_db_pool():
    print("Enumerando unidades...")
    unit_array = ctypes.POINTER(ctypes.c_uint32)()
    unit_count = ctypes.c_size_t(0)
    
    _winbio.WinBioEnumBiometricUnits(8, ctypes.byref(unit_array), ctypes.byref(unit_count))
    if unit_count.value == 0:
        return
        
    unit_id = unit_array[0]
    _winbio.WinBioFree(unit_array)
    
    unit_array_in = (ctypes.c_uint32 * 1)(unit_id)
    
    db_guid_bytes = bytes.fromhex("080000009c9d9a3acfe06942bda0b874")
    db_guid = ctypes.c_buffer(db_guid_bytes)
    
    handle = ctypes.c_uint32(0)
    
    print("Abriendo sesión privada...")
    hr2 = _winbio.WinBioOpenSession(
        8,  # WINBIO_TYPE_FINGERPRINT
        2,  # WINBIO_POOL_PRIVATE
        0,  # WINBIO_FLAG_BASIC
        unit_array_in,
        ctypes.c_size_t(1),
        db_guid,
        ctypes.byref(handle)
    )
    
    print(f"OpenSession HR: 0x{hr2 & 0xFFFFFFFF:08X}")
    if hr2 != 0:
        return
        
    captured_unit = wintypes.DWORD(0)
    print("Coloca tu dedo en el lector AHORA...")
    
    hr3 = _winbio.WinBioLocateSensor(handle, ctypes.byref(captured_unit))
    print(f"LocateSensor HR: 0x{hr3 & 0xFFFFFFFF:08X}")
    
    _winbio.WinBioCloseSession(handle)

if __name__ == "__main__":
    test_private_db_pool()
