# -*- coding: utf-8 -*-
"""
T3 网络验证 — 单文件集成版 (安全加固)
包含: 配置 + T3 SDK + 桥接逻辑, 无外部模块依赖
"""
import json
import time
import hashlib
import hmac
import uuid
import base64
from datetime import datetime
from pathlib import Path

# ═══════════════════════════════════════════════════════
#  配置区 (原 t3_config.py)
# ═══════════════════════════════════════════════════════

T3_CONFIG = {
    "appkey": "bccd408ab65984b6b9595b40f91b96c5",
    "login_code": "3E6A86D10AE3874A",
    "notice_code": "95B81F08041E1CF5",
    "version_code": "E416591C7C7F7717",
    "heartbeat_code": "0742C879E70634D5",
    "encode_type": "base64",
    "base64_charset": "c5Sm67NvWgFR9wVLACZrTl/DQubBJaOn12sYxHzMt0+XfPdoKkyq3GEi8Ij4pUeh",
    "rsa_public_key": """-----BEGIN PUBLIC KEY-----
YOUR_PUBLIC_KEY_HERE
-----END PUBLIC KEY-----""",
}

HEARTBEAT_INTERVAL = 300
APP_VERSION = "3.6.0"
_MAX_OFFLINE_HOURS = 72
SERVER_URL = "https://w.t3yanzheng.com/"


# ═══════════════════════════════════════════════════════
#  T3 SDK (原 t3sdk.py — 内联)
# ═══════════════════════════════════════════════════════

def get_machine_code():
    mac = uuid.getnode()
    return hashlib.md5(str(mac).encode()).hexdigest().upper()


class _CustomBase64:
    STANDARD = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

    def __init__(self, custom_charset):
        if len(custom_charset) != 64:
            raise ValueError("自定义字符集必须是64位字符")
        self.custom = custom_charset
        self.enc_tr = str.maketrans(self.STANDARD, self.custom)
        self.dec_tr = str.maketrans(self.custom, self.STANDARD)

    def encode(self, data):
        if isinstance(data, str):
            data = data.encode("utf-8")
        return base64.b64encode(data).decode("ascii").translate(self.enc_tr)

    def decode(self, data):
        return base64.b64decode(data.translate(self.dec_tr)).decode("utf-8")

    def encode_to_hex(self, data):
        return self.encode(data).encode("utf-8").hex().upper()


class _T3Core:
    """T3 网络验证核心"""
    def __init__(self):
        self.server_url = SERVER_URL
        self.login_code = None
        self.notice_code = None
        self.version_code = None
        self.heartbeat_code = None
        self.appkey = None
        self.encoder = None
        self.encode_type = "base64"
        self.statecode = None
        self.end_time = None

    def init(self, login_code, notice_code, version_code, heartbeat_code, appkey,
             base64_charset=None, rsa_public_key=None, encode_type="base64", **_kw):
        self.login_code = login_code
        self.notice_code = notice_code
        self.version_code = version_code
        self.heartbeat_code = heartbeat_code
        self.appkey = appkey
        self.encode_type = encode_type
        if encode_type == "base64":
            if not base64_charset:
                raise ValueError("Base64模式下必须提供 base64_charset")
            self.encoder = _CustomBase64(base64_charset)
        elif encode_type == "rsa":
            if not rsa_public_key:
                raise ValueError("RSA模式下必须提供 rsa_public_key")
            # RSA 模式需要 pycryptodome
            from Crypto.PublicKey import RSA as _RSA
            pem = rsa_public_key.strip()
            if not pem.startswith("-----BEGIN"):
                pem = "-----BEGIN PUBLIC KEY-----\n" + pem + "\n-----END PUBLIC KEY-----"
            self.rsa_key = _RSA.import_key(pem)
            self.rsa_key_size = self.rsa_key.size_in_bytes()
            self.rsa_enc_block = self.rsa_key_size - 11
            self.rsa_dec_block = self.rsa_key_size
        else:
            raise ValueError(f"不支持的加密类型: {encode_type}")

    def _encode_value(self, value):
        v = str(value)
        if self.encode_type == "base64":
            return self.encoder.encode_to_hex(v)
        else:
            from Crypto.Cipher import PKCS1_v1_5
            data = v.encode("utf-8")
            cipher = PKCS1_v1_5.new(self.rsa_key)
            enc = b""
            for i in range(0, len(data), self.rsa_enc_block):
                enc += cipher.encrypt(data[i:i + self.rsa_enc_block])
            return enc.hex().upper()

    def _decode_response(self, text):
        if self.encode_type == "base64":
            return self.encoder.decode(text)
        else:
            from Crypto.Util.number import bytes_to_long, long_to_bytes
            data = base64.b64decode(text)
            dec = b""
            n, e = self.rsa_key.n, self.rsa_key.e
            for i in range(0, len(data), self.rsa_dec_block):
                block = data[i:i + self.rsa_dec_block]
                bi = bytes_to_long(block)
                di = pow(bi, e, n)
                db = long_to_bytes(di, self.rsa_key_size)
                try:
                    pad_end = db.index(b"\x00", 2)
                    dec += db[pad_end + 1:]
                except ValueError:
                    dec += db
            return dec.decode("utf-8")

    def _encode_params(self, params):
        import requests
        ep = {}
        for k, v in params.items():
            ep[k] = self._encode_value(v)
        parts = [f"{k}={ep[k]}" for k in params]
        s_str = "&".join(parts) + "&" + self.appkey
        s_val = hashlib.md5(s_str.encode()).hexdigest().lower()
        ep["s"] = self._encode_value(s_val)
        return ep, s_str

    def _post(self, code, params):
        import requests
        url = f"{self.server_url.rstrip('/')}/{code}"
        params["t"] = int(time.time())
        ep, s_str = self._encode_params(params)
        resp = requests.post(url, data=ep, timeout=10)
        try:
            decoded = self._decode_response(resp.text)
        except Exception as e:
            return {"success": False, "error": f"响应解码失败: {e}"}
        try:
            jd = json.loads(decoded)
        except Exception:
            return {"success": False, "error": "响应不是有效的JSON格式"}
        return {"success": True, "data": jd, "s_str": s_str}

    def _simple_request(self, code, params):
        r = self._post(code, params)
        if not r["success"]:
            return r
        jd = r["data"]
        if jd.get("code") != 200 and str(jd.get("code")) != "200":
            return {"success": False, "error": jd.get("msg", "未知错误")}
        return {"success": True, "msg": jd.get("msg", "")}

    @staticmethod
    def _to_int(v):
        if v is None:
            return 0
        if isinstance(v, (int, float)):
            return int(v)
        try:
            return int(v)
        except (ValueError, TypeError):
            try:
                return int(datetime.strptime(v, "%Y-%m-%d %H:%M:%S").timestamp())
            except (ValueError, TypeError):
                try:
                    return int(datetime.strptime(v, "%Y-%m-%d").timestamp())
                except (ValueError, TypeError):
                    return 0

    def login(self, kami, imei):
        if not self.login_code:
            return {"success": False, "error": "未初始化"}
        r = self._post(self.login_code, {"kami": kami, "imei": imei})
        if not r["success"]:
            return r
        jd = r["data"]
        if jd.get("code") != 200:
            return {"success": False, "error": jd.get("msg", "未知错误")}

        e_raw = jd.get("end_time", "")
        t_raw = jd.get("time", "")
        e_int = self._to_int(e_raw)
        t_int = self._to_int(t_raw)
        kid = jd.get("id")
        token = jd.get("token")
        sc = jd.get("statecode")

        if not all([kid, e_raw, token, sc, t_raw]):
            return {"success": False, "error": "响应数据缺少必要字段"}
        if abs(int(time.time()) - t_int) > 5:
            return {"success": False, "error": f"时间戳校验失败"}
        ds = datetime.now().strftime("%Y%m%d%H%M")
        exp = hashlib.md5(f"{kid}{self.appkey}{r['s_str']}{e_raw}{ds}".encode()).hexdigest().lower()
        if token.lower() != exp:
            return {"success": False, "error": "token校验失败"}
        self.statecode = sc
        self.end_time = e_int
        return {
            "success": True,
            "id": kid,
            "end_time": e_int,
            "statecode": sc,
            "token": token,
            "imei": jd.get("imei"),
            "change": self._to_int(jd.get("change")),
            "core": jd.get("core"),
            "available": self._to_int(jd.get("available")),
            "amount": jd.get("amount"),
        }

    def heartbeat(self, kami, statecode):
        return self._simple_request(self.heartbeat_code, {"kami": kami, "statecode": statecode})

    def get_notice(self):
        r = self._simple_request(self.notice_code, {})
        if r["success"]:
            return {"success": True, "notice": r.get("msg", "")}
        return r

    def get_latest_version(self):
        r = self._simple_request(self.version_code, {})
        if r["success"]:
            return {"success": True, "version": r.get("msg", "")}
        return r

    def check_update(self, ver):
        r = self._simple_request(self.version_code, {"ver": ver})
        if r["success"]:
            return {"success": True, "has_update": False, "version": r.get("msg", "")}
        return r


# ═══════════════════════════════════════════════════════
#  安全加固 (机器码绑定 + HMAC签名 + 强制在线)
# ═══════════════════════════════════════════════════════

_verify = None
_kami = None
_statecode = None
_last_heartbeat = 0
_license_path = None


def _crypto_key():
    mc = get_machine_code()
    return hashlib.sha256(f"{mc}:{T3_CONFIG['appkey']}:af-secure-v2".encode()).digest()


def _xor_crypt(data_str):
    key = _crypto_key()
    data = data_str.encode("utf-8")
    return base64.b64encode(bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))).decode("ascii")


def _xor_decrypt(enc_b64):
    key = _crypto_key()
    data = base64.b64decode(enc_b64)
    return bytes(data[i] ^ key[i % len(key)] for i in range(len(data))).decode("utf-8")


def _sign(data_dict):
    key = _crypto_key()
    raw = json.dumps(data_dict, sort_keys=True, ensure_ascii=False)
    return hmac.new(key, raw.encode(), hashlib.sha256).hexdigest()


def _verify_sig(data_dict, signature):
    return hmac.compare_digest(_sign(data_dict), signature)


def _machine_hash():
    return hashlib.sha256(get_machine_code().encode()).hexdigest()[:16]


def _get_license_path():
    global _license_path
    if _license_path:
        return _license_path
    localappdata = (__import__("os").environ.get("LOCALAPPDATA")
                    or __import__("os").environ.get("APPDATA")
                    or str(Path.home()))
    p = Path(localappdata) / "AudioFlowStudio" / "license.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    _license_path = p
    return p


def _save_license(kami, statecode, payload):
    now = int(time.time())
    lic = {
        "v": 2,
        "mc_hash": _machine_hash(),
        "payload": payload,
        "sig": _sign(payload),
        "kami_enc": _xor_crypt(kami),
        "sc_enc": _xor_crypt(statecode),
        "verified_at": now,
        "last_online_at": now,
    }
    with open(_get_license_path(), "w", encoding="utf-8") as f:
        json.dump(lic, f, ensure_ascii=False, indent=2)


def _load_license():
    p = _get_license_path()
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            lic = json.load(f)
    except Exception:
        return None
    if lic.get("mc_hash") != _machine_hash():
        return None
    payload = lic.get("payload", {})
    if not payload or not _verify_sig(payload, lic.get("sig", "")):
        return None
    try:
        kami = _xor_decrypt(lic.get("kami_enc", ""))
        statecode = _xor_decrypt(lic.get("sc_enc", ""))
    except Exception:
        return None
    return {
        "kami": kami, "statecode": statecode,
        "payload": payload,
        "verified_at": lic.get("verified_at", 0),
        "last_online_at": lic.get("last_online_at", 0),
    }


def _update_last_online():
    p = _get_license_path()
    if not p.exists():
        return
    try:
        with open(p, "r", encoding="utf-8") as f:
            lic = json.load(f)
        lic["last_online_at"] = int(time.time())
        with open(p, "w", encoding="utf-8") as f:
            json.dump(lic, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _init_verify():
    global _verify
    if _verify is None:
        cfg = T3_CONFIG
        _verify = _T3Core()
        _verify.init(
            login_code=cfg["login_code"],
            notice_code=cfg["notice_code"],
            version_code=cfg["version_code"],
            heartbeat_code=cfg["heartbeat_code"],
            appkey=cfg["appkey"],
            encode_type=cfg["encode_type"],
            base64_charset=cfg.get("base64_charset"),
            rsa_public_key=cfg.get("rsa_public_key"),
        )
    return _verify


def _check_expired(payload):
    et = payload.get("expires_at", 0)
    if et and isinstance(et, (int, float)) and et < int(time.time()):
        return True
    return False


def _format_remaining(expires_at):
    if not expires_at:
        return "未知"
    try:
        et = int(expires_at)
    except (ValueError, TypeError):
        return "未知"
    if et > 9999999999:
        return "永久版"
    now = int(time.time())
    rem = et - now
    if rem <= 0:
        return "已过期"
    d, h = rem // 86400, (rem % 86400) // 3600
    if d > 365:
        return "永久版"
    if d > 0:
        return f"剩余 {d}天{h}小时"
    m = (rem % 3600) // 60
    return f"剩余 {h}小时{m}分钟"


# ═══════════════════════════════════════════════════════
#  license_client 接口
# ═══════════════════════════════════════════════════════

def machine_code():
    return get_machine_code()


def local_status():
    global _kami, _statecode
    saved = _load_license()
    if not saved:
        return (False, "未激活 — 请点击右上角「授权」输入卡密", {})
    _kami = saved["kami"]
    _statecode = saved["statecode"]
    payload = saved["payload"]
    if _check_expired(payload):
        return (False, "卡密已过期", payload)
    offline_secs = int(time.time()) - saved.get("last_online_at", 0)
    if offline_secs > _MAX_OFFLINE_HOURS * 3600:
        return (False, f"离线超时({_MAX_OFFLINE_HOURS}h) — 请联网后重启", payload)
    global _last_heartbeat
    if time.time() - _last_heartbeat > HEARTBEAT_INTERVAL:
        ok, _ = _do_heartbeat()
        if ok:
            _last_heartbeat = time.time()
            _update_last_online()
    return (True, _format_remaining(payload.get("expires_at", 0)), payload)


def online_verify():
    global _kami, _statecode, _last_heartbeat
    saved = _load_license()
    if not saved:
        return (False, "未激活 — 请先输入卡密激活", {})
    _kami = saved["kami"]
    _statecode = saved["statecode"]
    payload = saved["payload"]
    if _check_expired(payload):
        return (False, "卡密已过期", payload)
    ok, msg = _do_heartbeat()
    if ok:
        _last_heartbeat = time.time()
        _update_last_online()
        return (True, "在线验证通过", payload)
    last_online = saved.get("last_online_at", 0)
    offline_h = (int(time.time()) - last_online) // 3600
    remaining_h = _MAX_OFFLINE_HOURS - offline_h
    if remaining_h <= 0:
        return (False, "离线超时 — 请联网后重启验证", payload)
    return (True, f"{_format_remaining(payload.get('expires_at', 0))} — 离线 {remaining_h}h 后需联网", payload)


def activate_license(key):
    global _kami, _statecode
    key = key.strip().upper()
    if not key or len(key) < 8:
        return (False, "卡密格式无效", {})
    v = _init_verify()
    mc = get_machine_code()
    try:
        result = v.login(key, mc)
    except Exception as e:
        return (False, f"激活请求失败: {str(e)}", {})
    if not result.get("success"):
        err = result.get("error", "未知错误")
        if "不存在" in err or "not found" in err.lower():
            err = "卡密不存在，请检查是否输入正确"
        elif "已使用" in err or "used" in err.lower():
            err = "卡密已被使用"
        elif "过期" in err or "expired" in err.lower():
            err = "卡密已过期"
        elif "绑定" in err or "imei" in err.lower():
            err = "卡密已绑定其他设备"
        elif "禁用" in err or "disabled" in err.lower():
            err = "卡密已被禁用"
        elif "超时" in err or "timeout" in err.lower():
            err = "网络连接超时，请检查网络后重试"
        elif "连接" in err or "connection" in err.lower():
            err = "无法连接到验证服务器"
        return (False, err, {})
    _kami = key
    _statecode = result["statecode"]
    et = result.get("end_time", 0)
    payload = {
        "card_key": key,
        "card_type": "permanent" if (isinstance(et, (int, float)) and et > 999999999) else "subscription",
        "card_type_name": "永久版" if (isinstance(et, (int, float)) and et > 999999999) else f"到期:{et}",
        "machine_code": mc,
        "expires_at": et,
        "issued_at": int(time.time()),
        "card_id": result.get("id", ""),
    }
    _save_license(key, _statecode, payload)
    global _last_heartbeat
    _last_heartbeat = time.time()
    return (True, "激活成功！", payload)


def _do_heartbeat():
    global _kami, _statecode
    if not _kami or not _statecode:
        return (False, "未登录")
    v = _init_verify()
    try:
        r = v.heartbeat(_kami, _statecode)
    except Exception as e:
        return (False, f"心跳异常: {e}")
    return (r.get("success"), r.get("error", "心跳失败"))


def get_notice():
    v = _init_verify()
    try:
        return v.get_notice()
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_latest_version():
    v = _init_verify()
    try:
        return v.get_latest_version()
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_update():
    v = _init_verify()
    try:
        return v.check_update(APP_VERSION)
    except Exception as e:
        return {"success": False, "error": str(e)}
