# -*- coding: utf-8 -*-
"""
Ai Studio — Apple-Style UI (Complete Rewrite)
=============================================
Replaces main.pyc entirely. All business logic preserved via existing modules:
  engine, license_client, schemes, settings, platform_presets, updater, security_guard
"""
from __future__ import annotations

import os, sys, time, threading, re, subprocess, platform
from pathlib import Path

def _open_in_system(file_or_url: str):
    """Cross-platform open file/URL in system default handler."""
    if sys.platform == "darwin":
        subprocess.Popen(["open", file_or_url])
    elif sys.platform == "win32":
        os.startfile(file_or_url)
    else:
        subprocess.Popen(["xdg-open", file_or_url])

def _system_beep():
    """Cross-platform system beep."""
    if sys.platform == "win32":
        try:
            import winsound
            winsound.Beep(660, 120)
            winsound.Beep(880, 180)
        except Exception:
            print("\a")
    else:
        print("\a")

from PySide6.QtCore import Qt, QThread, Signal, QPoint, QTimer
from PySide6.QtGui import (
    QDragEnterEvent, QDropEvent, QFont, QMouseEvent, QIcon,
    QPalette, QColor, QFontDatabase, QAction,
)
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog,
    QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
    QProgressBar, QRadioButton, QScrollArea, QSpinBox, QTabWidget,
    QTextEdit, QPlainTextEdit, QVBoxLayout, QWidget, QInputDialog,
    QProgressDialog, QAbstractItemView, QStatusBar, QSizePolicy, QSpacerItem,
)

# QtWebEngine is needed for the Douyin Music browser tab.
# In dev mode, launcher.py puts PYZ.pyz_extracted (which has a stripped
# PySide6 without WebEngine) ahead of the system site-packages in sys.path.
# Work around this by putting the system site-packages first during import.
_HAS_WEBENGINE = False
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import (
        QWebEngineProfile, QWebEngineSettings, QWebEnginePage, QWebEngineDownloadRequest
    )
    _HAS_WEBENGINE = True
except ImportError:
    # PYZ.pyz_extracted is shadowing system PySide6 — fix sys.path and retry
    _site_paths = [p for p in sys.path if 'site-packages' in p and 'PYZ' not in p]
    for _sp in reversed(_site_paths):
        if _sp in sys.path:
            sys.path.remove(_sp)
        sys.path.insert(0, _sp)
    try:
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtWebEngineCore import (
            QWebEngineProfile, QWebEngineSettings, QWebEnginePage, QWebEngineDownloadRequest
        )
        _HAS_WEBENGINE = True
    except ImportError:
        pass

# Business logic — same as original
from engine import AudioEngine, collect_audio_files, format_duration, format_size
from license_client import activate_license, local_status, machine_code, online_verify
from platform_presets import PLATFORM_ORDER, PLATFORM_PRESETS
from schemes import SCHEMES, SCHEME_BY_ID
import settings

# ── License bypass: routes all calls through t3_bridge if available ──
try:
    import t3_bridge
    # Replace license_client functions with T3 bridge
    import license_client
    license_client.local_status = t3_bridge.local_status
    license_client.online_verify = t3_bridge.online_verify
    license_client.machine_code = t3_bridge.machine_code
    _orig_activate = t3_bridge.activate_license
    def _wrapped_activate(key):
        try: return _orig_activate(key)
        except Exception as e:
            try: QMessageBox.critical(None, "验证异常", f"发生错误:\n{str(e)}")
            except: pass
            return (False, f"内部错误: {str(e)}", {})
    license_client.activate_license = _wrapped_activate
except Exception:
    pass

# ── Settings branding override ──
settings.APP_NAME = "Ai Studio"
settings.CONTACT_TEXT = "问题咨询：QQ：88888888\n添加时备注来意"

def _contact_file():
    p = Path(settings.app_data_dir()) / "contact.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _exe_dir():
    try:
        if hasattr(sys, '_MEIPASS'):
            return Path(sys.executable).parent
    except: pass
    return Path(__file__).resolve().parent

def load_contact():
    # 1. 优先: EXE 旁边的 contact.txt (纯文本)
    try:
        cfg = _exe_dir() / "contact.txt"
        if cfg.exists():
            text = cfg.read_text("utf-8").strip()
            if text:
                return {"qq": "", "note": "", "custom": text}
    except: pass
    # 2. 其次: EXE 旁边的 contact.json (从⚙导出或手写)
    try:
        cfg = _exe_dir() / "contact.json"
        if cfg.exists():
            import json
            return json.loads(cfg.read_text("utf-8"))
    except: pass
    # 3. 再次: 本机用户通过⚙按钮改的
    try:
        if _contact_file().exists():
            import json
            return json.loads(_contact_file().read_text("utf-8"))
    except: pass
    # 4. 默认
    return {"qq": "88888888", "note": "来意", "custom": ""}

def save_contact(data):
    import json, traceback
    errors = []
    # Save to AppData
    try:
        _contact_file().write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    except Exception as e:
        errors.append(f"AppData: {e}")
    # Also save next to EXE (for distribution)
    try:
        cfg = _exe_dir() / "contact.json"
        cfg.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    except Exception as e:
        errors.append(f"EXE旁: {e}")
    if errors:
        return False, "\n".join(errors)
    return True, ""
settings.DEFAULT_OUTPUT_DIR = str(Path.home() / "Desktop" / "Ai_Studio_Output")


# ═══════════════════════════════════════════════════════════════
#  DOUYIN WEB ENGINE — intercept new-window requests
# ═══════════════════════════════════════════════════════════════

if _HAS_WEBENGINE:
    class _DouyinPopupWindow(QWidget):
        """Popup window for login / OAuth flows."""
        closed = Signal()

        def __init__(self, profile, parent=None):
            super().__init__(None, Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
            self.setWindowTitle("抖音登录")
            self.resize(480, 640)
            self.setMinimumSize(400, 500)
            lay = QVBoxLayout(self)
            lay.setContentsMargins(0, 0, 0, 0)
            self._webview = QWebEngineView(self)
            self._webview.setPage(QWebEnginePage(profile, self._webview))
            lay.addWidget(self._webview)
            if parent:
                pg = parent.geometry()
                self.move(pg.center() - self.rect().center())

        def webview(self):
            return self._webview

        def closeEvent(self, event):
            self.closed.emit()
            super().closeEvent(event)


    class _DouyinWebEnginePage(QWebEnginePage):
        """Custom page: login popups get their own window; tabs navigate in-place."""

        def __init__(self, profile, parent=None):
            super().__init__(profile, parent)
            self._main_view = parent

        def createWindow(self, _type):
            """WebBrowserWindow -> popup. WebBrowserTab -> in-place."""
            if _type == QWebEnginePage.WebWindowType.WebBrowserWindow:
                popup = _DouyinPopupWindow(self.profile(), self._main_view)
                popup.show()
                return popup.webview().page()
            else:
                new_page = QWebEnginePage(self.profile(), self._main_view)
                def _catch_url(url):
                    if url.isValid() and url.toString():
                        try:
                            new_page.urlChanged.disconnect(_catch_url)
                        except Exception:
                            pass
                        self._main_view.setUrl(url)
                new_page.urlChanged.connect(_catch_url)
                return new_page

        def acceptNavigationRequest(self, url, nav_type, is_main_frame):
            """Allow douyin.com and related OAuth domains."""
            host = url.host()
            url_str = url.toString()
            allowed = ["douyin.com", "bytedance.com", "byted.org",
                       "snssdk.com", "ixigua.com", "toutiao.com"]
            if any(d in host for d in allowed) or "douyin.com" in url_str:
                return True
            if nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
                import os
                try:
                    _open_in_system(url_str)
                except Exception:
                    pass
                return False
            return True




# ═══════════════════════════════════════════════════════════════
#  THEME SYSTEM, WIDGETS, MainWindow, ENTRY POINT
#  Reconstructed from Ai Studio main.py
# ═══════════════════════════════════════════════════════════════

THEME_MODE = "dark"

def _theme_path():
    p = Path(settings.app_data_dir()) / "theme.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def load_theme():
    global THEME_MODE
    try:
        import json
        tp = _theme_path()
        if tp.exists():
            THEME_MODE = json.loads(tp.read_text("utf-8")).get("mode", "dark")
    except: pass
    return THEME_MODE

def save_theme(mode):
    global THEME_MODE
    THEME_MODE = mode
    try:
        import json
        _theme_path().write_text(json.dumps({"mode": mode}), "utf-8")
    except: pass

class Colors:
    _instance = None
    def __init__(self, mode="dark"):
        if mode == "light":
            self.window = "#F5F5F7"; self.card = "#FFFFFF"; self.card_border = "#E5E5EA"
            self.text = "#1D1D1F"; self.text_secondary = "#86868B"
            self.accent = "#007AFF"; self.accent_hover = "#409CFF"; self.accent_pressed = "#0066CC"
            self.green = "#34C759"; self.red = "#FF3B30"; self.orange = "#FF9500"
            self.input_bg = "#FFFFFF"; self.input_border = "#C7C7CC"
            self.button_bg = "#FFFFFF"; self.button_border = "#C7C7CC"; self.button_hover = "#F5F5F7"
            self.surface = "#F9F9FB"; self.surface_border = "#E5E5EA"
            self.drop_border = "#C7C7CC"; self.divider = "#E5E5EA"
            self.scroll_handle = "rgba(0,0,0,0.15)"
            self.header_bg = "#FFFFFF"; self.status_bg = "#FFFFFF"
            self.card_checked_bg = "#EBF5FF"; self.card_checked_border = "#007AFF"
        else:
            self.window = "#16161A"; self.card = "#1C1C1E"; self.card_border = "#38383A"
            self.text = "#F5F5F7"; self.text_secondary = "#98989D"
            self.accent = "#0A84FF"; self.accent_hover = "#409CFF"; self.accent_pressed = "#0066CC"
            self.green = "#30D158"; self.red = "#FF453A"; self.orange = "#FF9F0A"
            self.input_bg = "#242426"; self.input_border = "#48484A"
            self.button_bg = "#2C2C2E"; self.button_border = "#48484A"; self.button_hover = "#3A3A3C"
            self.surface = "#242426"; self.surface_border = "#38383A"
            self.drop_border = "#48484A"; self.divider = "#2C2C2E"
            self.scroll_handle = "rgba(255,255,255,0.15)"
            self.header_bg = "#1C1C1E"; self.status_bg = "#1C1C1E"
            self.card_checked_bg = "#1A2A3A"; self.card_checked_border = "#0A84FF"

C = Colors()

def apply_global_theme(app, mode="dark"):
    global C; C = Colors(mode)
    p = QPalette()
    w = QColor(C.window); wt = QColor(C.text)
    b = QColor(C.card)
    h = QColor(C.accent); ht = QColor("#FFFFFF")
    p.setColor(QPalette.ColorRole.Window, w)
    p.setColor(QPalette.ColorRole.WindowText, wt)
    p.setColor(QPalette.ColorRole.Base, b)
    p.setColor(QPalette.ColorRole.AlternateBase, w)
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor(C.card))
    p.setColor(QPalette.ColorRole.ToolTipText, wt)
    p.setColor(QPalette.ColorRole.Text, wt)
    p.setColor(QPalette.ColorRole.Button, QColor(C.button_bg))
    p.setColor(QPalette.ColorRole.ButtonText, wt)
    p.setColor(QPalette.ColorRole.BrightText, h)
    p.setColor(QPalette.ColorRole.Link, h)
    p.setColor(QPalette.ColorRole.Highlight, h)
    p.setColor(QPalette.ColorRole.HighlightedText, ht)
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(C.text_secondary))
    app.setPalette(p)
    qss = f"""
    * {{ font-family: "Noto Sans SC", "Microsoft YaHei", "Segoe UI", sans-serif; font-size: 13px; outline: none; }}
    QMainWindow {{ background: {C.window}; }}
    QWidget {{ background: {C.window}; color: {C.text}; }}
    QFrame#panel, QFrame#card, QScrollArea {{ background: {C.card}; border: 1px solid {C.card_border}; border-radius: 16px; }}
    QFrame#dropBox {{ background: {C.card}; border: 2px dashed {C.drop_border}; border-radius: 16px; }}
    QFrame#schemeCard {{ background: {C.surface}; border: 1px solid {C.surface_border}; border-radius: 12px; }}
    QFrame#schemeCard[checked="true"] {{ background: {C.card_checked_bg}; border: 1.5px solid {C.card_checked_border}; }}
    QFrame#topBar {{ background: {C.header_bg}; border: none; border-bottom: 1px solid {C.divider}; border-radius: 0px; }}
    QLabel {{ background: transparent; color: {C.text}; font-size: 13px; }}
    QLabel#title {{ font-size: 20px; font-weight: 700; color: {C.text}; }}
    QLabel#section {{ font-size: 14px; font-weight: 600; color: {C.text}; }}
    QLabel#muted {{ color: {C.text_secondary}; font-size: 12px; }}
    QLabel#green {{ color: {C.green}; font-weight: 600; }}
    QLabel#blue {{ color: {C.accent}; font-weight: 600; }}
    QLabel#orange {{ color: {C.orange}; font-weight: 600; }}
    QLabel#tagGreen {{ color: {C.green}; font-size: 11px; font-weight: 700; }}
    QLabel#tagBlue {{ color: {C.accent}; font-size: 11px; font-weight: 700; }}
    QPushButton {{ background: {C.button_bg}; color: {C.text}; border: 1px solid {C.button_border}; border-radius: 18px; padding: 7px 16px; font-size: 13px; font-weight: 500; min-height: 28px; }}
    QPushButton:hover {{ background: {C.button_hover}; border-color: {C.accent}; }}
    QPushButton:pressed {{ background: {C.window}; }}
    QPushButton:disabled {{ background: {C.window}; color: {C.text_secondary}; border-color: {C.divider}; }}
    QPushButton#primary {{ background: {C.accent}; border: none; color: #FFFFFF; font-weight: 600; font-size: 14px; padding: 10px 24px; border-radius: 20px; }}
    QPushButton#primary:hover {{ background: {C.accent_hover}; }}
    QPushButton#primary:pressed {{ background: {C.accent_pressed}; }}
    QPushButton#ghost {{ background: transparent; border: 1px solid {C.button_border}; color: {C.text}; }}
    QPushButton#danger {{ background: transparent; border: 1px solid {C.red}; color: {C.red}; }}
    QPushButton#danger:hover {{ background: rgba(255,69,58,0.08); }}
    QPushButton#windowBtn {{ background: transparent; border: none; padding: 4px 10px; font-size: 15px; border-radius: 6px; min-height: 24px; min-width: 28px; }}
    QPushButton#windowBtn:hover {{ background: rgba(128,128,128,0.15); }}
    QPushButton#themeBtn {{ background: transparent; border: none; font-size: 17px; padding: 4px 6px; border-radius: 14px; min-height: 24px; min-width: 28px; }}
    QPushButton#themeBtn:hover {{ background: rgba(128,128,128,0.15); }}
    QPushButton#smallBtn {{ padding: 4px 10px; font-size: 12px; border-radius: 14px; min-height: 22px; }}
    QPushButton#pillGreen {{ background: transparent; border: 1px solid {C.green}; color: {C.green}; font-size: 11px; padding: 3px 10px; border-radius: 10px; font-weight: 600; min-height: 20px; }}
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ background: {C.input_bg}; border: 1px solid {C.input_border}; border-radius: 10px; padding: 7px 12px; color: {C.text}; font-size: 13px; selection-background-color: {C.accent}; }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {C.accent}; }}
    QComboBox::drop-down {{ border: none; width: 18px; }}
    QComboBox QAbstractItemView {{ background: {C.card}; border: 1px solid {C.card_border}; border-radius: 10px; color: {C.text}; padding: 4px; selection-background-color: rgba(128,128,128,0.15); }}
    QListWidget, QListView, QTreeView, QTableView {{ background: {C.surface}; border: 1px solid {C.surface_border}; border-radius: 12px; color: {C.text}; font-size: 13px; padding: 4px; }}
    QListWidget::item, QTreeView::item {{ padding: 7px 12px; border-radius: 6px; border: none; }}
    QListWidget::item:selected, QTreeView::item:selected {{ background: rgba(128,128,128,0.15); color: {C.text}; }}
    QListWidget::item:hover, QTreeView::item:hover {{ background: rgba(128,128,128,0.06); }}
    QProgressBar {{ background: {C.divider}; border: none; border-radius: 6px; text-align: center; color: {C.text}; font-size: 11px; height: 6px; }}
    QProgressBar::chunk {{ background: {C.accent}; border-radius: 6px; }}
    QScrollBar:vertical {{ background: transparent; width: 6px; border-radius: 3px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {C.scroll_handle}; border-radius: 3px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: rgba(128,128,128,0.3); }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{ background: transparent; height: 6px; border-radius: 3px; }}
    QScrollBar::handle:horizontal {{ background: {C.scroll_handle}; border-radius: 3px; min-width: 30px; }}
    QScrollBar::handle:horizontal:hover {{ background: rgba(128,128,128,0.3); }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    QGroupBox {{ border: 1px solid {C.card_border}; border-radius: 14px; margin-top: 14px; padding: 16px 12px 12px 12px; background: {C.card}; font-weight: 600; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {C.text_secondary}; }}
    QCheckBox, QRadioButton {{ background: transparent; color: {C.text}; font-size: 13px; spacing: 8px; }}
    QCheckBox::indicator, QRadioButton::indicator {{ width: 16px; height: 16px; border: 2px solid {C.text_secondary}; border-radius: 4px; background: transparent; }}
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{ background: {C.accent}; border-color: {C.accent}; }}
    QRadioButton::indicator {{ border-radius: 8px; }}
    QMenuBar {{ background: {C.header_bg}; border-bottom: 1px solid {C.divider}; }}
    QMenuBar::item:selected {{ background: rgba(128,128,128,0.1); }}
    QMenu {{ background: {C.card}; border: 1px solid {C.card_border}; border-radius: 10px; color: {C.text}; padding: 4px; }}
    QMenu::item {{ padding: 7px 20px; border-radius: 5px; }}
    QMenu::item:selected {{ background: rgba(128,128,128,0.12); }}
    QMenu::separator {{ height: 1px; background: {C.divider}; margin: 4px 8px; }}
    QToolTip {{ background: {C.card}; border: 1px solid {C.card_border}; color: {C.text}; font-size: 12px; padding: 7px 10px; border-radius: 8px; }}
    QStatusBar {{ background: {C.status_bg}; border-top: 1px solid {C.divider}; color: {C.text_secondary}; font-size: 12px; padding: 3px 10px; }}
    QTabWidget::pane {{ border: 1px solid {C.card_border}; border-radius: 14px; background: {C.card}; }}
    QTabBar::tab {{ background: {C.window}; border: 1px solid {C.divider}; border-bottom: none; padding: 7px 16px; color: {C.text_secondary}; }}
    QTabBar::tab:selected {{ background: {C.card}; color: {C.text}; font-weight: 600; }}
    QSplitter::handle {{ background: {C.divider}; width: 1px; height: 1px; }}
    """
    app.setStyleSheet(qss)
    save_theme(mode)


class DropArea(QFrame):
    files_dropped = Signal(list)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropBox")
        self.setAcceptDrops(True)
        self.setMinimumHeight(90)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label = QLabel("拖拽音频文件到此处\n支持 MP3 / WAV 格式")
        self._label.setObjectName("muted")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        lay.addWidget(self._label)
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(f"QFrame#dropBox {{ border: 2px dashed {C.accent}; }}")
        else: event.ignore()
    def dragLeaveEvent(self, event): self.setStyleSheet("")
    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        audio = [p for p in paths if Path(p).suffix.lower() in (".mp3", ".wav")]
        if audio: self.files_dropped.emit(audio)


class SchemeCard(QFrame):
    toggled = Signal(int, bool)
    def __init__(self, scheme: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("schemeCard")
        self._scheme = scheme
        self._checked = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(52)
        self._build()
    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 8, 14, 8); lay.setSpacing(12)
        self._check = QLabel("○")
        self._check.setObjectName("muted")
        self._check.setFont(QFont(self._check.font().family(), 16))
        self._check.setFixedWidth(24); lay.addWidget(self._check)
        info = QVBoxLayout(); info.setSpacing(2)
        name_lbl = QLabel(f"{self._scheme['num']} · {self._scheme['name']}")
        name_lbl.setStyleSheet("font-weight: 600;"); info.addWidget(name_lbl)
        desc = QLabel(self._scheme.get("desc", ""))
        desc.setObjectName("muted"); desc.setWordWrap(True); info.addWidget(desc)
        lay.addLayout(info, 1)
        tag = self._scheme.get("tag", "")
        if tag:
            badge = QLabel(tag); badge.setObjectName("pillGreen")
            badge.setFixedWidth(36); badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(badge)
    def mousePressEvent(self, event):
        self._checked = not self._checked; self._update_style()
        self.toggled.emit(self._scheme["index"], self._checked)
    def _update_style(self):
        if self._checked:
            self.setProperty("checked", True); self._check.setText("●")
            self._check.setObjectName("blue")
        else:
            self.setProperty("checked", False); self._check.setText("○")
            self._check.setObjectName("muted")
        self.style().unpolish(self); self.style().polish(self)
        self._check.style().unpolish(self._check); self._check.style().polish(self._check)
    @property
    def is_checked(self): return self._checked
    def set_checked(self, checked: bool):
        self._checked = checked; self._update_style()


class ActivationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("软件激活"); self.setFixedSize(420, 320)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24); lay.setSpacing(14)
        title = QLabel("请输入激活码"); title.setObjectName("section"); lay.addWidget(title)
        self._input = QLineEdit(); self._input.setPlaceholderText("输入激活码..."); lay.addWidget(self._input)
        self._status = QLabel(""); lay.addWidget(self._status)
        lay.addStretch()
        btn_row = QHBoxLayout(); btn_row.addStretch()
        activate_btn = QPushButton("激活"); activate_btn.setObjectName("primary")
        activate_btn.clicked.connect(self._do_activate)
        btn_row.addWidget(activate_btn); lay.addLayout(btn_row)
    def _do_activate(self):
        key = self._input.text().strip()
        if not key:
            self._status.setText("请输入激活码")
            self._status.setObjectName("orange"); return
        ok, msg, _ = license_client.activate_license(key)
        if ok:
            self._status.setText("激活成功!"); self._status.setObjectName("green")
            QTimer.singleShot(800, self.accept)
        else:
            self._status.setText(f"激活失败: {msg}"); self._status.setObjectName("orange")
        self._status.style().unpolish(self._status); self._status.style().polish(self._status)


class ProcessWorker(QThread):
    progress = Signal(int, str); log_msg = Signal(str); finished = Signal(str); failed = Signal(str)
    def __init__(self, files, scheme_indices, output_dir, fmt, parent=None):
        super().__init__(parent)
        self._files = files; self._scheme_indices = scheme_indices
        self._output_dir = output_dir; self._fmt = fmt
    def run(self):
        try:
            engine = AudioEngine(); total = len(self._files)
            for i, f in enumerate(self._files):
                fname = os.path.basename(f)
                self.log_msg.emit(f"处理: {fname}")
                for si in self._scheme_indices:
                    scheme = SCHEME_BY_ID.get(si)
                    if scheme: self.log_msg.emit(f"  方案: {scheme['name']}")
                base_pct = int(i * 100 / total)
                self.progress.emit(base_pct, f"处理中 {i+1}/{total}")
                def on_progress(sub_pct: int, msg: str):
                    overall = int((i * 100 + sub_pct) / total)
                    self.progress.emit(overall, f"{msg} ({i+1}/{total})")
                engine.process_pipeline(Path(f), self._output_dir, self._scheme_indices, self._fmt, progress=on_progress)
                finished_pct = int((i + 1) * 100 / total)
                self.progress.emit(finished_pct, f"已完成 {i+1}/{total}")
            self.finished.emit(f"完成: {total} 个文件")
        except Exception as e: self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ai Studio"); self.setMinimumSize(1280, 800); self.resize(1440, 900)
        self._files: list[str] = []; self._scheme_order: list[int] = []
        self._scheme_cards: dict[int, SchemeCard] = {}
        self._worker: ProcessWorker | None = None; self._drag_pos: QPoint | None = None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self._build_ui(); self._connect_signals()
        ok, _, _ = license_client.local_status()
        if not ok: QTimer.singleShot(200, self.show_license_dialog)

    def _build_ui(self):
        central = QWidget(); central.setObjectName("central"); self.setCentralWidget(central)
        main = QVBoxLayout(central); main.setContentsMargins(0, 0, 0, 0); main.setSpacing(0)
        main.addWidget(self._build_header())
        main.addWidget(self._build_body(), 1)
        main.addWidget(self._build_statusbar())

    def _build_header(self):
        header = QFrame(); header.setObjectName("topBar"); header.setFixedHeight(50)
        header.installEventFilter(self)
        lay = QHBoxLayout(header); lay.setContentsMargins(16, 0, 12, 0); lay.setSpacing(12)
        logo = QLabel("≋"); logo.setStyleSheet(f"font-size: 22px; color: {C.accent}; font-weight: 900; background: transparent;"); lay.addWidget(logo)
        title = QLabel("Ai Studio"); title.setObjectName("title"); lay.addWidget(title)
        version = QLabel(f"v{settings.APP_VERSION}"); version.setObjectName("muted"); lay.addWidget(version)
        lay.addStretch()
        contact = QPushButton("客服"); contact.setObjectName("ghost"); contact.setFixedHeight(30); contact.clicked.connect(self.show_contact_dialog); lay.addWidget(contact)
        edit_btn = QPushButton("设置"); edit_btn.setObjectName("smallBtn"); edit_btn.setFixedHeight(30); edit_btn.setToolTip("修改客服信息"); edit_btn.clicked.connect(self.edit_contact_dialog); lay.addWidget(edit_btn)
        self._lic_btn = QPushButton("授权"); self._lic_btn.setObjectName("ghost"); self._lic_btn.setFixedHeight(30); self._lic_btn.clicked.connect(self.show_license_dialog); lay.addWidget(self._lic_btn)
        self._lic_label = QLabel(""); self._lic_label.setObjectName("muted"); lay.addWidget(self._lic_label)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.VLine); sep.setStyleSheet(f"background: {C.divider}; min-width: 1px; max-width: 1px;"); sep.setFixedHeight(20); lay.addWidget(sep)
        theme_btn = QPushButton("☀️" if THEME_MODE == "dark" else "🌙"); theme_btn.setObjectName("themeBtn"); theme_btn.setToolTip("切换浅色/深色主题"); theme_btn.setCursor(Qt.CursorShape.PointingHandCursor); theme_btn.clicked.connect(self._toggle_theme); lay.addWidget(theme_btn)
        self._theme_btn = theme_btn
        mini = QPushButton("—"); mini.setObjectName("windowBtn"); mini.clicked.connect(self.showMinimized); lay.addWidget(mini)
        close_btn = QPushButton("✕"); close_btn.setObjectName("windowBtn"); close_btn.setStyleSheet(close_btn.styleSheet() + "QPushButton#windowBtn:hover { background: #FF3B30; color: #FFF; }"); close_btn.clicked.connect(self.close); lay.addWidget(close_btn)
        return header

    def _build_body(self):
        body_widget = QWidget()
        body = QHBoxLayout(body_widget); body.setContentsMargins(16, 12, 16, 16); body.setSpacing(16)
        body.addWidget(self._build_left_panel(), 2)
        body.addWidget(self._build_middle_panel(), 5)
        body.addWidget(self._build_right_panel(), 5)
        self._tabs = QTabWidget(); self._tabs.addTab(body_widget, "Ai Studio")
        if _HAS_WEBENGINE:
            douyin_browser = self._build_douyin_browser(); self._tabs.addTab(douyin_browser, "抖音音乐")
        else: self._log("QtWebEngine not available, Douyin tab skipped")
        return self._tabs

    def _build_douyin_browser(self):
        browser_widget = QWidget()
        lay = QVBoxLayout(browser_widget); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)
        profile_dir = str(settings.app_data_dir() / "DouyinWebProfile")
        profile = QWebEngineProfile("douyin_music", browser_widget)
        profile.setPersistentStoragePath(profile_dir)
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        settings_web = profile.settings()
        settings_web.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings_web.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings_web.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings_web.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        settings_web.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        self._douyin_webview = QWebEngineView()
        custom_page = _DouyinWebEnginePage(profile, self._douyin_webview)
        self._douyin_webview.setPage(custom_page)
        self._douyin_webview.setUrl("https://music.douyin.com/")
        self._douyin_webview.setMinimumWidth(900)
        profile.downloadRequested.connect(self._on_douyin_download)
        self._douyin_dl_dir = str(Path.home() / "Desktop" / "妙响已下载音乐")
        Path(self._douyin_dl_dir).mkdir(parents=True, exist_ok=True)
        self._douyin_known_files: set[str] = set()
        self._douyin_watch_timer = QTimer(self); self._douyin_watch_timer.setInterval(2000)
        self._douyin_watch_timer.timeout.connect(self._douyin_scan_downloads); self._douyin_watch_timer.start()
        lay.addWidget(self._douyin_webview)
        nav = QHBoxLayout(); nav.setContentsMargins(8, 4, 8, 4); nav.setSpacing(6)
        back_btn = QPushButton("◀"); back_btn.setObjectName("smallBtn"); back_btn.setToolTip("后退"); back_btn.clicked.connect(self._douyin_webview.back); nav.addWidget(back_btn)
        fwd_btn = QPushButton("▶"); fwd_btn.setObjectName("smallBtn"); fwd_btn.setToolTip("前进"); fwd_btn.clicked.connect(self._douyin_webview.forward); nav.addWidget(fwd_btn)
        refresh_btn = QPushButton("↻"); refresh_btn.setObjectName("smallBtn"); refresh_btn.setToolTip("刷新"); refresh_btn.clicked.connect(self._douyin_webview.reload); nav.addWidget(refresh_btn)
        self._douyin_url_bar = QLineEdit(); self._douyin_url_bar.setPlaceholderText("https://music.douyin.com/"); self._douyin_url_bar.returnPressed.connect(self._navigate_douyin); nav.addWidget(self._douyin_url_bar, 1)
        go_btn = QPushButton("→"); go_btn.setObjectName("smallBtn"); go_btn.setToolTip("跳转"); go_btn.clicked.connect(self._navigate_douyin); nav.addWidget(go_btn)
        lay.addLayout(nav)
        self._douyin_webview.urlChanged.connect(self._on_douyin_url_changed)
        return browser_widget

    def _navigate_douyin(self):
        text = self._douyin_url_bar.text().strip()
        if not text.startswith("http"): text = "https://" + text
        self._douyin_webview.setUrl(text)

    def _on_douyin_url_changed(self, url): self._douyin_url_bar.setText(url.toString())

    def _on_douyin_download(self, download: QWebEngineDownloadRequest):
        out_dir = str(Path.home() / "Desktop" / "妙响已下载音乐")
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        download.setDownloadDirectory(out_dir); download.accept()
        self._log(f"抖音下载: {download.downloadFileName()}")

    def _douyin_scan_downloads(self):
        import os as _os
        out_dir = self._douyin_dl_dir
        if not _os.path.isdir(out_dir): return
        try: entries = _os.listdir(out_dir)
        except Exception: return
        for name in entries:
            full = _os.path.join(out_dir, name)
            ext = _os.path.splitext(name)[1].lower()
            if ext not in (".mp3", ".wav"): continue
            if full in self._douyin_known_files: continue
            if full in self._files: self._douyin_known_files.add(full); continue
            try: size1 = _os.path.getsize(full)
            except Exception: continue
            if not hasattr(self, '_douyin_pending'): self._douyin_pending: dict[str, tuple[int, int]] = {}
            prev = self._douyin_pending.get(full)
            if prev is not None and prev[0] == size1:
                del self._douyin_pending[full]; self._douyin_known_files.add(full)
                self.add_paths([full]); self._log(f"已从抖音导入: {name}")
            else: self._douyin_pending[full] = (size1, 0)

    def _build_left_panel(self):
        panel = QFrame(); panel.setObjectName("panel")
        lay = QVBoxLayout(panel); lay.setContentsMargins(16, 16, 16, 16); lay.setSpacing(12)
        header = QLabel("输入文件"); header.setObjectName("section"); lay.addWidget(header)
        self._drop = DropArea(); self._drop.files_dropped.connect(self.add_paths); lay.addWidget(self._drop)
        self._file_list = QListWidget(); self._file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection); lay.addWidget(self._file_list, 1)
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        add_btn = QPushButton("＋ 添加"); add_btn.setObjectName("smallBtn"); add_btn.clicked.connect(self.add_files); btn_row.addWidget(add_btn)
        folder_btn = QPushButton("文件夹"); folder_btn.setObjectName("smallBtn"); folder_btn.clicked.connect(self.add_folder); btn_row.addWidget(folder_btn)
        clear_btn = QPushButton("清空"); clear_btn.setObjectName("smallBtn"); clear_btn.clicked.connect(self.clear_files); btn_row.addWidget(clear_btn)
        remove_btn = QPushButton("移除"); remove_btn.setObjectName("smallBtn"); remove_btn.clicked.connect(self.remove_selected_files); btn_row.addWidget(remove_btn)
        btn_row.addStretch(); lay.addLayout(btn_row)
        return panel

    def _build_middle_panel(self):
        panel = QFrame(); panel.setObjectName("panel")
        lay = QVBoxLayout(panel); lay.setContentsMargins(16, 16, 16, 16); lay.setSpacing(12)
        header = QLabel("处理方案"); header.setObjectName("section"); lay.addWidget(header)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_widget = QWidget(); self._scheme_layout = QVBoxLayout(scroll_widget)
        self._scheme_layout.setSpacing(6); self._scheme_layout.setContentsMargins(0, 0, 0, 0)
        for s in SCHEMES:
            card = SchemeCard(s); card.toggled.connect(self._on_scheme_toggled)
            self._scheme_layout.addWidget(card); self._scheme_cards[s["index"]] = card
        self._scheme_layout.addStretch(); scroll.setWidget(scroll_widget); lay.addWidget(scroll, 1)
        preset_label = QLabel("平台预设"); preset_label.setObjectName("section"); preset_label.setStyleSheet("margin-top: 8px;"); lay.addWidget(preset_label)
        preset_row = QHBoxLayout(); preset_row.setSpacing(6)
        self._preset_btns: dict[str, QPushButton] = {}
        for pname in PLATFORM_ORDER:
            btn = QPushButton(pname); btn.setObjectName("smallBtn"); btn.setCheckable(True)
            btn.clicked.connect(lambda n=pname, b=btn: self._on_preset(n, b.isChecked()))
            preset_row.addWidget(btn); self._preset_btns[pname] = btn
        preset_row.addStretch(); lay.addLayout(preset_row)
        order_label = QLabel("方案顺序"); order_label.setObjectName("section"); order_label.setStyleSheet("margin-top: 8px;"); lay.addWidget(order_label)
        self._order_list = QListWidget(); self._order_list.setMaximumHeight(100); lay.addWidget(self._order_list)
        order_btn_row = QHBoxLayout(); order_btn_row.setSpacing(6)
        up_btn = QPushButton("↑ 上移"); up_btn.setObjectName("smallBtn"); up_btn.clicked.connect(lambda: self.move_scheme(-1)); order_btn_row.addWidget(up_btn)
        down_btn = QPushButton("↓ 下移"); down_btn.setObjectName("smallBtn"); down_btn.clicked.connect(lambda: self.move_scheme(1)); order_btn_row.addWidget(down_btn)
        remove_s_btn = QPushButton("✕ 移除"); remove_s_btn.setObjectName("smallBtn"); remove_s_btn.clicked.connect(self.remove_scheme_from_order); order_btn_row.addWidget(remove_s_btn)
        select_all_btn = QPushButton("全选"); select_all_btn.setObjectName("smallBtn"); select_all_btn.clicked.connect(self._select_all_schemes); order_btn_row.addWidget(select_all_btn)
        order_btn_row.addStretch(); lay.addLayout(order_btn_row)
        return panel

    def _build_right_panel(self):
        panel = QFrame(); panel.setObjectName("panel")
        lay = QVBoxLayout(panel); lay.setContentsMargins(16, 16, 16, 16); lay.setSpacing(14)
        header = QLabel("处理设置"); header.setObjectName("section"); lay.addWidget(header)
        mode_label = QLabel("处理模式"); mode_label.setStyleSheet("font-weight: 600;"); lay.addWidget(mode_label)
        mode_row = QHBoxLayout(); mode_row.setSpacing(2); self._mode_group = QButtonGroup(self)
        self._mode_pipeline = QPushButton("流水线"); self._mode_pipeline.setCheckable(True); self._mode_pipeline.setChecked(True); self._mode_pipeline.setObjectName("smallBtn")
        self._mode_single = QPushButton("单方案"); self._mode_single.setCheckable(True); self._mode_single.setObjectName("smallBtn")
        self._mode_group.addButton(self._mode_pipeline); self._mode_group.addButton(self._mode_single); self._mode_group.setExclusive(True)
        mode_row.addWidget(self._mode_pipeline); mode_row.addWidget(self._mode_single); mode_row.addStretch(); lay.addLayout(mode_row)
        fmt_label = QLabel("输出格式"); fmt_label.setStyleSheet("font-weight: 600;"); lay.addWidget(fmt_label)
        self._format_combo = QComboBox(); self._format_combo.addItems(["WAV", "MP3"]); lay.addWidget(self._format_combo)
        wrk_label = QLabel("并发数"); wrk_label.setStyleSheet("font-weight: 600;"); lay.addWidget(wrk_label)
        self._worker_spin = QSpinBox(); self._worker_spin.setRange(1, 8); self._worker_spin.setValue(2); lay.addWidget(self._worker_spin)
        out_label = QLabel("输出目录"); out_label.setStyleSheet("font-weight: 600;"); lay.addWidget(out_label)
        out_row = QHBoxLayout(); out_row.setSpacing(8)
        self._output_edit = QLineEdit(); self._output_edit.setText(settings.DEFAULT_OUTPUT_DIR); out_row.addWidget(self._output_edit, 1)
        browse_btn = QPushButton("选择"); browse_btn.setObjectName("smallBtn"); browse_btn.clicked.connect(self.choose_output_dir); out_row.addWidget(browse_btn)
        open_btn = QPushButton("打开"); open_btn.setObjectName("smallBtn"); open_btn.setToolTip("打开输出目录"); open_btn.clicked.connect(self.open_output_dir); out_row.addWidget(open_btn)
        lay.addLayout(out_row); lay.addStretch()
        self._progress = QProgressBar(); self._progress.setValue(0); self._progress.setTextVisible(True); self._progress.setFormat("%p%"); lay.addWidget(self._progress)
        self._progress_label = QLabel("就绪"); self._progress_label.setObjectName("muted"); self._progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter); lay.addWidget(self._progress_label)
        log_label = QLabel("运行日志"); log_label.setStyleSheet("font-weight: 600; margin-top: 8px;"); lay.addWidget(log_label)
        self._log_view = QPlainTextEdit(); self._log_view.setReadOnly(True); self._log_view.setMaximumBlockCount(500); self._log_view.setMinimumHeight(100); self._log_view.setPlaceholderText("处理日志将显示在这里..."); lay.addWidget(self._log_view, 1)
        action_row = QHBoxLayout(); action_row.setSpacing(12)
        self._start_btn = QPushButton("开始处理"); self._start_btn.setObjectName("primary"); self._start_btn.setMinimumHeight(40); self._start_btn.clicked.connect(self.start_processing); action_row.addWidget(self._start_btn, 1)
        self._stop_btn = QPushButton("停止"); self._stop_btn.setObjectName("danger"); self._stop_btn.setMinimumHeight(40); self._stop_btn.setEnabled(False); self._stop_btn.clicked.connect(self.stop_processing); action_row.addWidget(self._stop_btn)
        lay.addLayout(action_row)
        return panel

    def _build_statusbar(self):
        self._statusbar = QStatusBar(); self._statusbar.showMessage("就绪"); return self._statusbar

    def _connect_signals(self):
        self._lic_timer = QTimer(); self._lic_timer.setInterval(1000); self._lic_timer.timeout.connect(self._refresh_license); self._lic_timer.start(); self._refresh_license()

    def eventFilter(self, obj, event):
        if obj.objectName() == "topBar":
            if event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft(); return True
            if event.type() == event.Type.MouseMove and self._drag_pos is not None:
                self.move(event.globalPosition().toPoint() - self._drag_pos); return True
            if event.type() == event.Type.MouseButtonRelease: self._drag_pos = None; return True
        return super().eventFilter(obj, event)

    def _toggle_theme(self):
        new_mode = "light" if THEME_MODE == "dark" else "dark"
        apply_global_theme(QApplication.instance(), new_mode)
        self._theme_btn.setText("☀️" if new_mode == "dark" else "🌙")
        self._theme_btn.setToolTip("切换浅色主题" if new_mode == "dark" else "切换深色主题")

    def _refresh_license(self):
        try:
            ok, msg, _ = license_client.local_status()
            if ok: self._lic_label.setText(f" {msg}"); self._lic_label.setObjectName("green"); self._lic_btn.hide()
            else: self._lic_label.setText(" 未激活"); self._lic_label.setObjectName("orange"); self._lic_btn.show()
            self._lic_label.style().unpolish(self._lic_label); self._lic_label.style().polish(self._lic_label)
        except: pass

    def show_license_dialog(self):
        dlg = ActivationDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted: self._refresh_license()

    def show_contact_dialog(self):
        info = load_contact()
        qq = info.get("qq", "")
        if qq: text = f"问题咨询：QQ：{qq}" + (f"\n添加时备注{info['note']}" if info.get("note") else "")
        elif info.get("custom"): text = info["custom"]
        else: text = "暂无客服信息"
        QMessageBox.information(self, "联系客服", text)

    def edit_contact_dialog(self):
        info = load_contact()
        dlg = QDialog(self); dlg.setWindowTitle("修改客服信息"); dlg.setFixedSize(420, 380)
        lay = QVBoxLayout(dlg); lay.setContentsMargins(20, 20, 20, 20); lay.setSpacing(10)
        title = QLabel("自定义客服信息"); title.setObjectName("section"); lay.addWidget(title)
        qq_row = QHBoxLayout(); qq_row.addWidget(QLabel("QQ号:"))
        qq_input = QLineEdit(info.get("qq", "")); qq_input.setPlaceholderText("输入QQ号"); qq_row.addWidget(qq_input); lay.addLayout(qq_row)
        note_row = QHBoxLayout(); note_row.addWidget(QLabel("备注:"))
        note_input = QLineEdit(info.get("note", "")); note_input.setPlaceholderText("添加时备注内容"); note_row.addWidget(note_input); lay.addLayout(note_row)
        url_row = QHBoxLayout(); url_row.addWidget(QLabel("更新链接:"))
        url_input = QLineEdit(info.get("update_url", "")); url_input.setPlaceholderText("新版本下载链接，发给用户后自动提示更新"); url_row.addWidget(url_input); lay.addLayout(url_row)
        lay.addWidget(QLabel("或直接输入完整信息:"))
        custom_input = QTextEdit(); custom_input.setPlaceholderText("自定义客服信息（支持多行）\n例如：\n微信：xxx\n电话：xxx"); custom_input.setPlainText(info.get("custom", "")); custom_input.setMaximumHeight(60); lay.addWidget(custom_input)
        btn_row = QHBoxLayout(); btn_row.addStretch()
        cancel = QPushButton("取消"); cancel.setObjectName("ghost"); cancel.clicked.connect(dlg.reject); btn_row.addWidget(cancel)
        save_btn = QPushButton("保存"); save_btn.setObjectName("primary")
        def do_save():
            ok, err = save_contact({"qq": qq_input.text().strip(), "note": note_input.text().strip(), "custom": custom_input.toPlainText().strip(), "update_url": url_input.text().strip()})
            if ok: QMessageBox.information(dlg, "已保存", "客服信息已更新"); dlg.accept()
            else: QMessageBox.critical(dlg, "保存失败", f"无法保存:\n{err}")
        save_btn.clicked.connect(do_save); btn_row.addWidget(save_btn); lay.addLayout(btn_row)
        dlg.exec()

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "导入音频", "", "Audio Files (*.mp3 *.wav);;MP3 (*.mp3);;WAV (*.wav)")
        if paths: self.add_paths(paths)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            files = collect_audio_files(folder)
            if files: self.add_paths(files)
            else: QMessageBox.information(self, "提示", "所选文件夹中没有 MP3/WAV 文件")

    def add_paths(self, paths: list[str]):
        added = 0
        for p in paths:
            p = os.path.abspath(p)
            if p not in self._files: self._files.append(p); self._file_list.addItem(os.path.basename(p)); added += 1
        self._log(f"已添加 {added} 个文件，共 {len(self._files)} 个")

    def clear_files(self): self._files.clear(); self._file_list.clear(); self._log("已清空文件列表")

    def remove_selected_files(self):
        for item in self._file_list.selectedItems():
            idx = self._file_list.row(item)
            if 0 <= idx < len(self._files): self._files.pop(idx); self._file_list.takeItem(idx)

    def _on_scheme_toggled(self, index: int, checked: bool):
        if checked:
            if index not in self._scheme_order: self._scheme_order.append(index)
        else:
            if index in self._scheme_order: self._scheme_order.remove(index)
        self._refresh_order_ui()

    def _refresh_order_ui(self):
        self._order_list.clear()
        for i in self._scheme_order:
            s = SCHEME_BY_ID.get(i)
            if s: self._order_list.addItem(f"{s['num']} · {s['name']}")

    def move_scheme(self, direction: int):
        row = self._order_list.currentRow()
        if row < 0 or row >= len(self._scheme_order): return
        new_row = row + direction
        if 0 <= new_row < len(self._scheme_order):
            self._scheme_order[row], self._scheme_order[new_row] = self._scheme_order[new_row], self._scheme_order[row]
            self._refresh_order_ui(); self._order_list.setCurrentRow(new_row)

    def remove_scheme_from_order(self):
        row = self._order_list.currentRow()
        if row < 0 or row >= len(self._scheme_order): return
        idx = self._scheme_order.pop(row)
        if idx in self._scheme_cards: self._scheme_cards[idx].set_checked(False)
        self._refresh_order_ui()

    def _select_all_schemes(self):
        all_checked = all(card.is_checked for card in self._scheme_cards.values())
        for card in self._scheme_cards.values(): card.set_checked(not all_checked)
        self._scheme_order.clear()
        if not all_checked:
            for s in SCHEMES: self._scheme_order.append(s["index"])
        self._refresh_order_ui()

    def _on_preset(self, name: str, checked: bool):
        if checked and name in PLATFORM_PRESETS:
            preset = PLATFORM_PRESETS[name]; scheme_ids = preset.get("schemes", [])
            for card in self._scheme_cards.values(): card.set_checked(False)
            self._scheme_order.clear()
            for sid in scheme_ids:
                if sid in self._scheme_cards: self._scheme_cards[sid].set_checked(True); self._scheme_order.append(sid)
            self._refresh_order_ui(); self._log(f"已应用预设: {name}")
            QTimer.singleShot(500, lambda: self._preset_btns[name].setChecked(False))

    def choose_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if folder: self._output_edit.setText(folder)

    def open_output_dir(self):
        out_dir = self._output_edit.text()
        if out_dir and os.path.exists(out_dir): _open_in_system(out_dir)
        else: QMessageBox.information(self, "提示", "输出目录不存在")

    def start_processing(self):
        if not self._files: QMessageBox.warning(self, "提示", "请先导入音频文件"); return
        if not self._scheme_order: QMessageBox.warning(self, "提示", "请至少选择一个处理方案"); return
        out_dir = self._output_edit.text() or settings.DEFAULT_OUTPUT_DIR; fmt = self._format_combo.currentText().lower()
        self._start_btn.setEnabled(False); self._stop_btn.setEnabled(True); self._progress.setValue(0); self._progress_label.setText("正在处理...")
        self._worker = ProcessWorker(self._files, self._scheme_order, out_dir, fmt)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.log_msg.connect(lambda m: self._log(m))
        self._worker.finished.connect(self._on_finished); self._worker.failed.connect(self._on_failed)
        self._worker.start()
        self._log(f"开始处理 {len(self._files)} 个文件，{len(self._scheme_order)} 个方案")

    def _on_worker_progress(self, value: int, text: str):
        self._progress.setValue(value)
        self._progress_label.setText(text)

    def stop_processing(self):
        if self._worker and self._worker.isRunning(): self._worker.terminate(); self._worker.wait(2000)
        self._start_btn.setEnabled(True); self._stop_btn.setEnabled(False); self._progress_label.setText("已停止"); self._log("处理已停止")

    def _on_finished(self, msg: str):
        self._progress.setValue(100); self._progress_label.setText(" " + msg)
        self._start_btn.setEnabled(True); self._stop_btn.setEnabled(False); self._log(msg)
        _system_beep()

    def _on_failed(self, msg: str):
        self._progress_label.setText(" " + msg); self._start_btn.setEnabled(True); self._stop_btn.setEnabled(False)
        self._log(msg); QMessageBox.warning(self, "处理失败", msg)

    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S"); line = f"[{ts}] {msg}"
        self._statusbar.showMessage(msg)
        if hasattr(self, '_log_view') and self._log_view: self._log_view.appendPlainText(line)


def main():
    try:
        from security_guard import runtime_guard_ok
        if not runtime_guard_ok: QMessageBox.critical(None, "错误", "运行环境异常"); sys.exit(1)
    except Exception: pass
    load_theme()
    app = QApplication(sys.argv); app.setApplicationName("Ai Studio"); app.setApplicationVersion(settings.APP_VERSION)
    try:
        base = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(__file__).resolve().parent
        font_path = str(base / "assets" / "NotoSansSC.ttf")
        if os.path.exists(font_path): QFontDatabase.addApplicationFont(font_path)
    except: pass
    try:
        base = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(__file__).resolve().parent
        icon_path = str(base / "assets" / "favicon.ico")
        if os.path.exists(icon_path): app.setWindowIcon(QIcon(icon_path))
    except: pass
    apply_global_theme(app, THEME_MODE)
    win = MainWindow(); win.show()

    def do_check_update():
        try:
            import t3_bridge
            def _parse_t3_response(resp):
                if resp.get("success") and resp.get("version"):
                    ver = resp["version"].strip(); url = ""
                    if "|" in ver: ver, url = ver.split("|", 1)
                    return ver.strip(), url.strip()
                err = resp.get("error", "")
                if "|" in err and err[0].isdigit():
                    parts = err.split("|", 1)
                    return parts[0].strip(), parts[1].strip() if len(parts) > 1 else ""
                return "", ""
            notice = t3_bridge.get_notice()
            notice_msg = notice.get("notice", "") if notice.get("success") else notice.get("error", "")
            if notice_msg and notice_msg.strip():
                urls = re.findall(r'https?://\S+', notice_msg)
                if urls:
                    box = QMessageBox(win); box.setWindowTitle("公告"); box.setText(notice_msg)
                    open_btn = box.addButton("打开链接", QMessageBox.ButtonRole.AcceptRole)
                    box.addButton("关闭", QMessageBox.ButtonRole.RejectRole); box.exec()
                    if box.clickedButton() == open_btn: _open_in_system(urls[0])
                else: QMessageBox.information(win, "公告", notice_msg)
            latest = t3_bridge.get_latest_version()
            latest_ver, t3_url = _parse_t3_response(latest)
            if latest_ver:
                current_ver = settings.APP_VERSION.strip()
                if latest_ver != current_ver:
                    info = load_contact(); update_url = t3_url or info.get("update_url", "")
                    if update_url:
                        box = QMessageBox(win); box.setWindowTitle("必须更新")
                        box.setText(f"检测到新版本 {latest_ver}\n当前版本 {current_ver} 已停用\n\n点击「下载更新」获取最新版本")
                        box.setIcon(QMessageBox.Icon.Warning); box.setStandardButtons(QMessageBox.StandardButton.NoButton)
                        box.addButton("下载更新", QMessageBox.ButtonRole.AcceptRole); box.exec()
                        _open_in_system(update_url); QApplication.quit(); return
                    else:
                        QMessageBox.critical(win, "必须更新", f"检测到新版本 {latest_ver}\n当前版本 {current_ver} 已停用\n\n请联系客服获取最新安装包")
                        QApplication.quit(); return
        except Exception: pass
    QTimer.singleShot(2000, do_check_update)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
