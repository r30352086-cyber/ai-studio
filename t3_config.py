# -*- coding: utf-8 -*-
"""
T3 网络验证配置
从 T3 管理后台获取: https://www.t3yanzheng.com
"""

T3_CONFIG = {
    # ========== 必填: 程序密钥 ==========
    # T3后台 → 应用管理 → APPKEY
    "appkey": "bccd408ab65984b6b9595b40f91b96c5",

    # ========== 必填: 调用码 (从 T3 后台获取) ==========
    # T3后台 → 应用管理 → 接口管理 → 对应接口的调用码
    "login_code": "3E6A86D10AE3874A",
    "notice_code": "95B81F08041E1CF5",
    "version_code": "E416591C7C7F7717",
    "heartbeat_code": "0742C879E70634D5",

    # ========== 加密模式 ==========
    # "base64" — 无需额外依赖，推荐
    # "rsa"    — 需要 pycryptodome 库，加密更强
    "encode_type": "base64",

    # ========== Base64 模式 (encode_type="base64" 时必填) ==========
    # T3后台 → 传输配置 → 自定义编码集 (64个字符)
    "base64_charset": "c5Sm67NvWgFR9wVLACZrTl/DQubBJaOn12sYxHzMt0+XfPdoKkyq3GEi8Ij4pUeh",

    # ========== RSA 模式 (encode_type="rsa" 时必填) ==========
    # T3后台 → 传输配置 → RSA公钥
    "rsa_public_key": """-----BEGIN PUBLIC KEY-----
YOUR_PUBLIC_KEY_HERE
-----END PUBLIC KEY-----""",
}

# ========== 心跳间隔 (秒) ==========
HEARTBEAT_INTERVAL = 300  # 5分钟

# ========== 应用版本号 ==========
# T3后台设置的版本号需与此对应
APP_VERSION = "3.6.0"
