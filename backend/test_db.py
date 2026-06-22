import ctypes
from ctypes import wintypes

_winbio = ctypes.windll.winbio

class WINBIO_STORAGE_SCHEMA(ctypes.Structure):
    _fields_ = [
        ("DatabaseId", ctypes.c_byte * 16),
        ("DataFormat", ctypes.c_uint32),
        ("Attributes", ctypes.c_uint32),
        ("Description", ctypes.c_wchar * 256),
        ("Vendor", ctypes.c_wchar * 256),
        ("Model", ctypes.c_wchar * 256),
    ]

_winbio.WinBioEnumDatabases.argtypes = [
    ctypes.c_uint32,
    ctypes.POINTER(ctypes.POINTER(WINBIO_STORAGE_SCHEMA)),
    ctypes.POINTER(ctypes.c_size_t)
]

schema_array = ctypes.POINTER(WINBIO_STORAGE_SCHEMA)()
schema_count = ctypes.c_size_t(0)

hr = _winbio.WinBioEnumDatabases(8, ctypes.byref(schema_array), ctypes.byref(schema_count))
print(f"EnumDatabases HR: 0x{hr & 0xFFFFFFFF:08X}, Count: {schema_count.value}")

if hr == 0 and schema_count.value > 0:
    for i in range(schema_count.value):
        db_id = schema_array[i].DatabaseId
        guid_bytes = bytes(db_id)
        print(f"DB {i} ID:", guid_bytes.hex())

if schema_array:
    _winbio.WinBioFree(schema_array)
