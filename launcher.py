# -*- coding: utf-8 -*-
"""
Ai Studio — Launcher
====================
- Suppresses console windows from subprocess calls
- Sets up paths for frozen/development environments
- Injects license bypass (T3 verification)
- Delegates all UI to main.py
"""
import sys, os
from pathlib import Path

# ── Suppress subprocess console windows ──
import subprocess as _sp
_orig_popen = _sp.Popen.__init__
def _no_console_popen(self, *a, **kw):
    if sys.platform == "win32":
        kw.setdefault("creationflags", 0)
        kw["creationflags"] |= 0x08000000  # CREATE_NO_WINDOW
        if "startupinfo" not in kw:
            si = _sp.STARTUPINFO()
            si.dwFlags |= 0x00000001
            si.wShowWindow = 0
            kw["startupinfo"] = si
    _orig_popen(self, *a, **kw)
_sp.Popen.__init__ = _no_console_popen

import os as _os
_orig_system = _os.system
def _no_console_system(cmd):
    if sys.platform == "win32":
        try:
            si = _sp.STARTUPINFO()
            si.dwFlags |= 0x00000001
            si.wShowWindow = 0
            return _sp.call(cmd, shell=True, creationflags=0x08000000, startupinfo=si)
        except: pass
    return _orig_system(cmd)
_os.system = _no_console_system


def get_base():
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def setup_paths(base):
    pyz = base / "PYZ.pyz_extracted"
    for p in [str(pyz), str(base)]:
        if p not in sys.path:
            sys.path.insert(0, p)
    tools_dir = base / "tools"
    if tools_dir.exists():
        os.environ["PATH"] = str(tools_dir) + os.pathsep + os.environ.get("PATH", "")
    sox = tools_dir / "sox-14-4-2"
    if sox.exists():
        os.environ["PATH"] = str(sox) + os.pathsep + os.environ.get("PATH", "")


def inject_license_bypass(base):
    """Replace original license backend with T3 verification."""
    import settings
    settings.APP_NAME = "Ai Studio"
    settings.CONTACT_TEXT = "问题咨询：QQ：88888888\n添加时备注来意"
    settings.DEFAULT_OUTPUT_DIR = str(Path.home() / "Desktop" / "Ai_Studio_Output")

    try:
        import t3_bridge, license_client
        license_client.local_status = t3_bridge.local_status
        license_client.online_verify = t3_bridge.online_verify
        license_client.machine_code = t3_bridge.machine_code
        _orig_activate = t3_bridge.activate_license
        def _wrapped_activate(key):
            try: return _orig_activate(key)
            except Exception as e:
                try:
                    from PySide6.QtWidgets import QMessageBox, QApplication
                    app = QApplication.instance()
                    if app: QMessageBox.critical(None, "验证异常", str(e))
                except: pass
                return (False, f"内部错误: {str(e)}", {})
        license_client.activate_license = _wrapped_activate
    except Exception:
        pass  # t3_bridge not available — use original license flow

    # ── Robust tool path lookup ──
    try:
        import engine
        _orig_find_tool = engine.AudioEngine._find_tool
        def _robust_find_tool(self, filename, in_sox=False):
            result = _orig_find_tool(self, filename, in_sox)
            if result is not None: return result
            bp = Path(sys._MEIPASS) / "tools"
            p = (bp / "sox-14-4-2" / filename) if in_sox else (bp / filename)
            if p.exists(): return p.resolve()
            import shutil; found = shutil.which(filename)
            return Path(found).resolve() if found else None
        engine.AudioEngine._find_tool = _robust_find_tool
    except Exception: pass

    # ── Fix: output filename matches imported filename (no scheme prefix) ──
    try:
        import engine as _engine
        _orig_process_pipeline = _engine.AudioEngine.process_pipeline
        def _fixed_process_pipeline(self, src, out_dir, scheme_ids, fmt, progress=None, platform_code=None):
            # Call the original pipeline — it builds output as:
            #   {out_dir}/{safe_name(src.name)}_{'-'.join(map(str,scheme_ids))}.{ext}
            result = _orig_process_pipeline(self, src, out_dir, scheme_ids, fmt, progress, platform_code)

            # Rename output: use original filename only (no scheme suffix)
            import re as _re
            src_path = Path(src) if not isinstance(src, Path) else src
            base = _engine.safe_name(src_path.name)
            suffix = '-'.join(str(int(i)) for i in scheme_ids)
            engine_ext = '.wav'
            # Check if last scheme forces MP3
            from schemes import SCHEME_BY_ID
            if scheme_ids:
                last_id = int(scheme_ids[-1])
                last_scheme = SCHEME_BY_ID.get(last_id)
                if last_scheme and last_scheme.get('force_mp3'):
                    engine_ext = '.mp3'
            generated_name = f"{base}_{suffix}{engine_ext}"
            generated_path = Path(out_dir) / generated_name

            # Rename to match original filename
            def _try_rename(src_p, dst_p):
                try:
                    if not src_p.exists() or src_p == dst_p:
                        return False
                    if dst_p.exists():
                        dst_p.unlink()
                    src_p.rename(dst_p)
                    return True
                except Exception:
                    return False

            desired_ext = f".{fmt.lower()}" if fmt else engine_ext
            desired_path = Path(out_dir) / f"{base}{desired_ext}"

            renamed = _try_rename(generated_path, desired_path)

            # Fallback: scan output dir for engine-generated files matching pattern
            if not renamed:
                pattern = _re.compile(
                    _re.escape(base) + r'_[-\d]+' + _re.escape(engine_ext) + r'$'
                )
                try:
                    for entry in sorted(Path(out_dir).iterdir(), key=lambda e: e.stat().st_mtime, reverse=True):
                        if entry.is_file() and pattern.match(entry.name):
                            if _try_rename(entry, desired_path):
                                break
                except Exception:
                    pass

            return result
        _engine.AudioEngine.process_pipeline = _fixed_process_pipeline
    except Exception:
        pass


if __name__ == "__main__":
    base = get_base()
    setup_paths(base)
    inject_license_bypass(base)

    # ── Delegate to main.py for all UI ──
    from main import main
    main()
