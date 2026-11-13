"""Everything that differs between a Mac and a Windows PC, in one place (AVS launcher, standard library only).

Downloads with their pinned checksums, where a venv keeps its Python, how to open a folder or page, the real Desktop,
free disk, memory, the chip and the system version, and the Microsoft C++ runtime check (Windows Phase 0: torch and
MediaPipe load msvcp140, msvcp140_1 and concrt140 from Windows itself, so a PC without them fails).
"""
import ctypes
import os
import platform
import shutil
import subprocess
import sys

WIN = sys.platform == 'win32'
MAC = sys.platform == 'darwin'
EXE = '.exe' if WIN else ''

NODE_VERSION = '22.23.3'
UV_VERSION = '0.12.22'
PY_VERSION = '3.12'
FFMPEG_WIN = '9.0.2'
MEDIAPIPE = '0.10.21'
YTDLP = '2026.8.19'   # PyPI spelling of yt-dlp 2026.08.19

# (url, sha256) per system; every Windows download is checked (Mac ffmpeg keeps install.sh's unchecked "latest")
NODE = {
    'win-x64': ('https://nodejs.org/dist/v%s/node-v%s-win-x64.zip' % (NODE_VERSION, NODE_VERSION),
                '2b0ff57b049cda1bbcea2240eec20467018713c1efe1f7360c2681859b90ed71'),
    'darwin-arm64': ('https://nodejs.org/dist/v%s/node-v%s-darwin-arm64.tar.gz' % (NODE_VERSION, NODE_VERSION),
                     '23b25245dcfb9af7262f8ff142e9e2e0af025368117329e7a7458a51e5922f53'),
    'darwin-x64': ('https://nodejs.org/dist/v%s/node-v%s-darwin-x64.tar.gz' % (NODE_VERSION, NODE_VERSION),
                   '8a677b0219178efd6eb0e475457c4afb452b521a92f6e67845a73bd85727f2a8'),
}
UV = {
    'win-x64': ('https://github.com/astral-sh/uv/releases/download/%s/uv-x86_64-pc-windows-msvc.zip' % UV_VERSION,
                'ea1397797a0ca15f63516dd0f49c2dde9776db9be5861cab152ebe8ad199894d'),
    'darwin-arm64': ('https://github.com/astral-sh/uv/releases/download/%s/uv-aarch64-apple-darwin.tar.gz' % UV_VERSION,
                     '5d714de09501a59393ceca78f4bc232a50478729640d251907160299b2a93ddd'),
    'darwin-x64': ('https://github.com/astral-sh/uv/releases/download/%s/uv-x86_64-apple-darwin.tar.gz' % UV_VERSION,
                   '1b8a5b316883df2daf20fb9a446e5b230e01d947d57aba2694977c5ac5a7e98c'),
}
FFMPEG = {
    'win-x64': ('https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-%s-essentials_build.zip' % FFMPEG_WIN,
                '60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba'),
}
CUTOUT_MODEL = ('https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/latest/'
                'selfie_multiclass_256x256.tflite', 'c6748b1253a99067ef71f7e26ca71096cd449baefa8f101900ea23016507e0e0')
YTDLP_MAC = ('https://github.com/yt-dlp/yt-dlp/releases/download/2026.08.19/yt-dlp_macos',
             '0f192b7ec147ab6288885d6351d9ab67367640029b4377576ef46dd79cf7b202')
CPP_RUNTIME = ('msvcp140.dll', 'msvcp140_1.dll', 'vcruntime140.dll', 'vcruntime140_1.dll', 'concrt140.dll')
CPP_RUNTIME_URL = 'https://aka.ms/vs/17/release/vc_redist.x64.exe'


def native_machine():
    """'x64' or 'arm64' for the chip itself, even when this process runs emulated (an x64 Python on an ARM PC)."""
    if WIN:
        try:
            k = ctypes.windll.kernel32
            proc, native = ctypes.c_ushort(0), ctypes.c_ushort(0)
            if k.IsWow64Process2(ctypes.c_void_p(k.GetCurrentProcess()), ctypes.byref(proc), ctypes.byref(native)):
                return {0xAA64: 'arm64', 0x8664: 'x64'}.get(native.value, 'other %#x' % native.value)
        except Exception:
            pass
        a = (os.environ.get('PROCESSOR_ARCHITEW6432') or os.environ.get('PROCESSOR_ARCHITECTURE') or '').upper()
        return 'arm64' if 'ARM' in a else 'x64'
    if MAC:
        try:   # an Intel Python on an Apple chip still reports the chip here
            if subprocess.run(['sysctl', '-n', 'hw.optional.arm64'], capture_output=True, text=True).stdout.strip() == '1':
                return 'arm64'
        except Exception:
            pass
        return 'arm64' if platform.machine() == 'arm64' else 'x64'
    return platform.machine()


def key():
    """The download key for this computer: win-x64, darwin-arm64, darwin-x64."""
    return ('win-' if WIN else 'darwin-') + native_machine()


def system():
    """(name, version tuple, words) e.g. ('windows', (10, 0, 26100), 'Windows 11 (build 26100)')."""
    if WIN:
        v = tuple(int(x) for x in platform.version().split('.')[:3])
        return 'windows', v, '%s (build %d)' % ('Windows 11' if v[2] >= 22000 else 'Windows 10', v[2])
    if MAC:
        s = platform.mac_ver()[0] or '0'
        return 'macos', tuple(int(x) for x in s.split('.')), 'macOS %s' % s
    return sys.platform, (0,), sys.platform


def free_gb(path):
    while not os.path.exists(path):
        path = os.path.dirname(path)
    return shutil.disk_usage(path).free / 1e9


def ram_gb():
    """The memory installed, in GB (the number Windows Settings shows). AVS_TEST_RAM_GB stands in for it in the tests."""
    if os.environ.get('AVS_TEST_RAM_GB'):
        return float(os.environ['AVS_TEST_RAM_GB'])
    try:
        if WIN:
            kb = ctypes.c_ulonglong(0)
            if ctypes.windll.kernel32.GetPhysicallyInstalledSystemMemory(ctypes.byref(kb)) and kb.value:
                return kb.value / 2 ** 20
            class M(ctypes.Structure):
                _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong), ('ullTotalPhys', ctypes.c_ulonglong),
                            ('ullAvailPhys', ctypes.c_ulonglong), ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                            ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong), ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
            m = M(); m.dwLength = ctypes.sizeof(M)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullTotalPhys / 2 ** 30
        return int(subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True).stdout) / 2 ** 30
    except Exception:
        return 0.0


def cpp_runtime_missing():
    """The Microsoft C++ runtime files this PC lacks (empty on a Mac, and on any PC that has them)."""
    if not WIN:
        return []
    d = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32')
    return [f for f in CPP_RUNTIME if not os.path.exists(os.path.join(d, f))]


def venv_python(venv):
    return os.path.join(venv, 'Scripts', 'python.exe') if WIN else os.path.join(venv, 'bin', 'python')


def venv_bin(venv):
    return os.path.join(venv, 'Scripts' if WIN else 'bin')


def node_exe(rt):
    return os.path.join(rt, 'node', 'node.exe') if WIN else os.path.join(rt, 'node', 'bin', 'node')


def npm_cli(rt):
    return os.path.join(rt, 'node', 'node_modules', 'npm', 'bin', 'npm-cli.js') if WIN else \
        os.path.join(rt, 'node', 'lib', 'node_modules', 'npm', 'bin', 'npm-cli.js')


def desktop():
    """The folder the person sees as their Desktop (on many PCs it lives inside OneDrive)."""
    if WIN:
        try:
            from ctypes import wintypes
            class GUID(ctypes.Structure):
                _fields_ = [('a', wintypes.DWORD), ('b', wintypes.WORD), ('c', wintypes.WORD), ('d', ctypes.c_ubyte * 8)]
            g = GUID(0xB4BFCC3A, 0xDB2C, 0x424C, (ctypes.c_ubyte * 8)(0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41))   # FOLDERID_Desktop
            p = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(p)) == 0:
                out = p.value
                ctypes.windll.ole32.CoTaskMemFree(p)
                return out
        except Exception:
            pass
    return os.path.join(os.path.expanduser('~'), 'Desktop')


def open_path(p):
    """Open a folder in Finder / File Explorer, or a page in the default browser."""
    if WIN:
        os.startfile(p)
    else:
        subprocess.run(['open', p], check=False)


def curl():
    return 'curl.exe' if WIN else 'curl'
