import ctypes, ctypes.wintypes as w, importlib, sys
done = []
for m in sys.argv[1:]:
    try:
        importlib.import_module(m); done.append(m)
    except Exception as e:
        done.append('%s (import failed: %s)' % (m, type(e).__name__))
psapi, k32 = ctypes.WinDLL('psapi'), ctypes.WinDLL('kernel32')
k32.GetCurrentProcess.restype = w.HANDLE
psapi.EnumProcessModules.argtypes = [w.HANDLE, ctypes.POINTER(w.HMODULE), w.DWORD, ctypes.POINTER(w.DWORD)]
psapi.GetModuleFileNameExW.argtypes = [w.HANDLE, w.HMODULE, w.LPWSTR, w.DWORD]
h = k32.GetCurrentProcess(); arr = (w.HMODULE * 8192)(); need = w.DWORD()
psapi.EnumProcessModules(h, arr, ctypes.sizeof(arr), ctypes.byref(need))
buf = ctypes.create_unicode_buffer(2048); names = []
for i in range(need.value // ctypes.sizeof(w.HMODULE)):
    psapi.GetModuleFileNameExW(h, arr[i], buf, 2048); names.append(buf.value)
rt = ('vcruntime', 'msvcp', 'vcomp', 'concrt', 'libomp', 'vccorlib')
sysrt = sorted({n.split('\\')[-1].lower() for n in names if n.lower().startswith('c:\\windows') and any(t in n.lower() for t in rt)})
own = sorted({n.split('\\')[-1].lower() for n in names if not n.lower().startswith('c:\\windows') and any(t in n.lower() for t in rt)})
print('imported: %s; Microsoft C++ runtime from Windows: %s; bundled inside the packages: %s' % (', '.join(done), ', '.join(sysrt) or 'none', ', '.join(own) or 'none'))
