# -*- coding: utf-8 -*-
"""
T3网络验证 Python SDK v2.0.0
https://www.t3yanzheng.com

扁平化版本 — 单文件可直接放入 PyInstaller build 目录
"""

import requests
import time
import hashlib
from datetime import datetime
import base64
import json
import uuid


SERVER_URL = 'https://w.t3yanzheng.com/'


def get_machine_code():
    mac = uuid.getnode()
    machine_code = hashlib.md5(str(mac).encode()).hexdigest().upper()
    return machine_code


class CustomBase64:
    STANDARD_CHARSET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'

    def __init__(self, custom_charset):
        if len(custom_charset) != 64:
            raise ValueError("自定义字符集必须是64位字符")
        self.custom_charset = custom_charset
        self.encode_trans = str.maketrans(self.STANDARD_CHARSET, self.custom_charset)
        self.decode_trans = str.maketrans(self.custom_charset, self.STANDARD_CHARSET)

    def encode(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        standard_b64 = base64.b64encode(data).decode('ascii')
        custom_b64 = standard_b64.translate(self.encode_trans)
        return custom_b64

    def decode(self, data):
        standard_b64 = data.translate(self.decode_trans)
        decoded_bytes = base64.b64decode(standard_b64)
        return decoded_bytes.decode('utf-8')

    def encode_to_hex(self, data):
        encoded = self.encode(data)
        hex_str = encoded.encode('utf-8').hex().upper()
        return hex_str


class RSACrypto:
    """RSA 加解密工具类

    使用 RSA/ECB/PKCS1Padding 模式，支持分段加密/解密。
    - 加密：公钥加密，分段大小 = keySize - 11 (1024位密钥为117字节)
    - 解密：公钥解密(验证私钥签名)，分段大小 = keySize (1024位密钥为128字节)
    """

    def __init__(self, public_key_pem):
        """初始化 RSA 加解密器

        Args:
            public_key_pem: PEM 格式的 RSA 公钥字符串
        """
        from Crypto.PublicKey import RSA
        # 清理公钥格式
        pem = public_key_pem.strip()
        if not pem.startswith('-----BEGIN'):
            pem = '-----BEGIN PUBLIC KEY-----\n' + pem + '\n-----END PUBLIC KEY-----'
        self.public_key = RSA.import_key(pem)
        self.key_size = self.public_key.size_in_bytes()  # 1024位 = 128字节
        self.encrypt_block_size = self.key_size - 11      # 117字节
        self.decrypt_block_size = self.key_size            # 128字节

    def encrypt(self, data):
        """RSA 公钥加密（分段, PKCS1_v1_5）"""
        from Crypto.Cipher import PKCS1_v1_5
        cipher = PKCS1_v1_5.new(self.public_key)
        data_bytes = data.encode('utf-8') if isinstance(data, str) else data

        encrypted = b''
        offset = 0
        while offset < len(data_bytes):
            block = data_bytes[offset:offset + self.encrypt_block_size]
            encrypted += cipher.encrypt(block)
            offset += self.encrypt_block_size

        return encrypted

    def decrypt(self, encrypted_data):
        """RSA 公钥解密（分段, 用于解密服务端私钥加密的数据）"""
        from Crypto.Util.number import bytes_to_long, long_to_bytes

        decrypted = b''
        offset = 0
        n = self.public_key.n
        e = self.public_key.e

        while offset < len(encrypted_data):
            block = encrypted_data[offset:offset + self.decrypt_block_size]
            block_int = bytes_to_long(block)
            decrypted_int = pow(block_int, e, n)
            decrypted_block = long_to_bytes(decrypted_int, self.key_size)
            try:
                pad_end = decrypted_block.index(b'\x00', 2)
                decrypted += decrypted_block[pad_end + 1:]
            except ValueError:
                decrypted += decrypted_block
            offset += self.decrypt_block_size

        return decrypted.decode('utf-8')

    def encrypt_to_hex(self, data):
        """RSA 公钥加密后转为 HEX 大写字符串"""
        encrypted = self.encrypt(data)
        return encrypted.hex().upper()

    def decrypt_from_base64(self, base64_str):
        """从 Base64 字符串解码后进行 RSA 公钥解密"""
        encrypted_data = base64.b64decode(base64_str)
        return self.decrypt(encrypted_data)


class T3Verify:
    def __init__(self):
        self.server_url = SERVER_URL
        # 已有调用码
        self.login_code = None
        self.notice_code = None
        self.version_code = None
        self.heartbeat_code = None
        # 新增调用码
        self.query_code = None
        self.register_code = None
        self.user_login_code = None
        self.user_heartbeat_code = None
        self.qq_login_code = None
        self.bind_qq_code = None
        self.change_password_code = None
        self.user_cancel_code = None
        self.recharge_code = None
        self.unbind_code = None
        self.ip_unbind_code = None
        self.disable_code = None
        self.check_update_code = None
        self.get_variable_code = None
        self.modify_variable_code = None
        self.modify_core_code = None
        self.get_kami_core_code = None
        self.get_user_core_code = None
        self.online_kami_code = None
        self.online_user_code = None
        self.cloud_doc_code = None
        self.app_sign_code = None
        # 公共配置
        self.appkey = None
        self.base64_charset = None
        self.encoder = None
        self.rsa_crypto = None
        self.encode_type = 'base64'
        self.statecode = None
        self.end_time = None

    def init(self, login_code, notice_code, version_code, heartbeat_code, appkey,
             base64_charset=None, rsa_public_key=None, encode_type='base64',
             # 新增调用码（全部可选）
             query_code=None, register_code=None, user_login_code=None,
             user_heartbeat_code=None, qq_login_code=None, bind_qq_code=None,
             change_password_code=None, user_cancel_code=None, recharge_code=None,
             unbind_code=None, ip_unbind_code=None, disable_code=None,
             check_update_code=None, get_variable_code=None, modify_variable_code=None,
             modify_core_code=None, get_kami_core_code=None, get_user_core_code=None,
             online_kami_code=None, online_user_code=None,
             cloud_doc_code=None, app_sign_code=None):
        """初始化 T3 验证 SDK

        Args:
            login_code: 单码登录调用码
            notice_code: 获取程序公告调用码
            version_code: 获取程序最新版本号调用码
            heartbeat_code: 单码卡密心跳验证调用码
            appkey: 程序密钥 APPKEY
            base64_charset: Base64自定义编码集（base64模式必填）
            rsa_public_key: RSA公钥 PEM 字符串（rsa模式必填）
            encode_type: 加密算法类型，'base64' 或 'rsa'
            query_code: 查询卡密调用码
            register_code: 用户注册调用码
            user_login_code: 用户登录调用码
            user_heartbeat_code: 用户心跳调用码
            qq_login_code: QQ登录调用码
            bind_qq_code: 绑定QQ调用码
            change_password_code: 修改密码调用码
            user_cancel_code: 用户注销调用码
            recharge_code: 用户充值调用码
            unbind_code: 解绑设备调用码
            ip_unbind_code: IP解绑调用码
            disable_code: 禁用调用码
            check_update_code: 检查更新调用码
            get_variable_code: 获取变量调用码
            modify_variable_code: 修改变量调用码
            modify_core_code: 修改核心数据调用码
            get_kami_core_code: 获取卡密核心数据调用码
            get_user_core_code: 获取用户核心数据调用码
            online_kami_code: 获取在线卡密数量调用码
            online_user_code: 获取在线用户数量调用码
            cloud_doc_code: 云文档调用码
            app_sign_code: 应用签名调用码
        """
        # 已有调用码
        self.login_code = login_code
        self.notice_code = notice_code
        self.version_code = version_code
        self.heartbeat_code = heartbeat_code
        self.appkey = appkey
        self.encode_type = encode_type
        # 新增调用码
        self.query_code = query_code
        self.register_code = register_code
        self.user_login_code = user_login_code
        self.user_heartbeat_code = user_heartbeat_code
        self.qq_login_code = qq_login_code
        self.bind_qq_code = bind_qq_code
        self.change_password_code = change_password_code
        self.user_cancel_code = user_cancel_code
        self.recharge_code = recharge_code
        self.unbind_code = unbind_code
        self.ip_unbind_code = ip_unbind_code
        self.disable_code = disable_code
        self.check_update_code = check_update_code
        self.get_variable_code = get_variable_code
        self.modify_variable_code = modify_variable_code
        self.modify_core_code = modify_core_code
        self.get_kami_core_code = get_kami_core_code
        self.get_user_core_code = get_user_core_code
        self.online_kami_code = online_kami_code
        self.online_user_code = online_user_code
        self.cloud_doc_code = cloud_doc_code
        self.app_sign_code = app_sign_code

        if encode_type == 'base64':
            self.base64_charset = base64_charset
            if not base64_charset:
                raise ValueError("Base64模式下必须提供 base64_charset 参数")
            try:
                self.encoder = CustomBase64(base64_charset)
            except ValueError as e:
                raise ValueError(f"初始化Base64编码器失败: {e}")
        elif encode_type == 'rsa':
            if not rsa_public_key:
                raise ValueError("RSA模式下必须提供 rsa_public_key 参数")
            try:
                self.rsa_crypto = RSACrypto(rsa_public_key)
            except Exception as e:
                raise ValueError(f"初始化RSA加密器失败: {e}")
        else:
            raise ValueError(f"不支持的加密类型: {encode_type}，仅支持 'base64' 或 'rsa'")

    def _check_init(self):
        if not self.appkey:
            raise ValueError("未初始化，请先调用 init() 方法")

    def _check_code(self, code, name):
        """检查调用码是否已设置"""
        if not code:
            raise ValueError(f"未设置 {name} 调用码，请在 init() 中配置")

    def _build_url(self, code):
        if self.server_url.endswith('/'):
            return f"{self.server_url}{code}"
        else:
            return f"{self.server_url}/{code}"

    def _encode_value(self, value):
        """统一编码入口：根据 encode_type 选择编码方式"""
        value_str = str(value)
        if self.encode_type == 'base64':
            return self.encoder.encode_to_hex(value_str)
        else:
            return self.rsa_crypto.encrypt_to_hex(value_str)

    def _decode_response(self, response_text):
        """统一解码入口：根据 encode_type 选择解码方式"""
        try:
            if self.encode_type == 'base64':
                return self.encoder.decode(response_text)
            else:
                return self.rsa_crypto.decrypt_from_base64(response_text)
        except Exception as e:
            raise ValueError(f"响应解码失败: {e}")

    def _encode_params(self, params):
        """编码所有参数并生成签名

        关键：每个参数值只加密一次！
        RSA 的 PKCS1_v1_5 填充含随机性，同一明文每次加密结果不同，
        必须用同一个加密值同时构建签名字符串和 POST 数据。
        """
        encoded_params = {}
        for key, value in params.items():
            encoded_params[key] = self._encode_value(value)

        parts = []
        for key in params:
            parts.append(f"{key}={encoded_params[key]}")
        s_string = '&'.join(parts)
        s_string += '&' + self.appkey

        s_value = hashlib.md5(s_string.encode()).hexdigest().lower()
        encoded_params['s'] = self._encode_value(s_value)

        return encoded_params, s_string

    def _simple_request(self, code, code_name, params):
        """通用简单请求：发送参数，返回 {success, error/msg}"""
        try:
            self._check_init()
            self._check_code(code, code_name)
            url = self._build_url(code)
            t = int(time.time())
            params['t'] = t
            encoded_data, _ = self._encode_params(params)
            response = requests.post(url, data=encoded_data, timeout=10)
            try:
                decoded_response = self._decode_response(response.text)
            except Exception as e:
                return {'success': False, 'error': f'响应解码失败: {str(e)}'}
            try:
                json_data = json.loads(decoded_response)
            except:
                return {'success': False, 'error': '响应不是有效的JSON格式'}
            if json_data.get('code') != 200 and str(json_data.get('code')) != '200':
                return {'success': False, 'error': json_data.get('msg', '未知错误')}
            return {'success': True, 'msg': json_data.get('msg', '')}
        except ValueError as e:
            return {'success': False, 'error': str(e)}
        except requests.exceptions.Timeout:
            return {'success': False, 'error': '请求超时'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': '连接错误'}
        except Exception as e:
            return {'success': False, 'error': f'未知错误: {str(e)}'}

    # ==================== 卡密验证 ====================

    def login(self, kami, imei):
        """单码卡密登录"""
        try:
            self._check_init()
            self._check_code(self.login_code, '单码登录')
            url = self._build_url(self.login_code)
            t = int(time.time())
            post_data = {'kami': kami, 'imei': imei, 't': t}
            encoded_data, s_original = self._encode_params(post_data)
            response = requests.post(url, data=encoded_data, timeout=10)
            try:
                decoded_response = self._decode_response(response.text)
            except Exception as e:
                return {'success': False, 'error': f'响应解码失败: {str(e)}'}
            try:
                json_data = json.loads(decoded_response)
            except:
                return {'success': False, 'error': '响应不是有效的JSON格式'}
            if json_data.get('code') != 200:
                return {'success': False, 'error': json_data.get('msg', '未知错误')}
            # 安全转换：服务端可能返回字符串或数字
            def _to_int(v):
                if v is None:
                    return 0
                if isinstance(v, (int, float)):
                    return int(v)
                try:
                    return int(v)
                except (ValueError, TypeError):
                    # 可能是日期时间字符串
                    try:
                        return int(datetime.strptime(v, "%Y-%m-%d %H:%M:%S").timestamp())
                    except (ValueError, TypeError):
                        try:
                            return int(datetime.strptime(v, "%Y-%m-%d").timestamp())
                        except (ValueError, TypeError):
                            return 0

            # ── 保留原始值用于 token 计算 ──
            kami_id = json_data.get('id')
            end_time_raw = json_data.get('end_time', '')
            token = json_data.get('token')
            statecode = json_data.get('statecode')
            response_time_raw = json_data.get('time', '')
            core = json_data.get('core')
            imei = json_data.get('imei')
            use_time = json_data.get('use_time')
            available_raw = json_data.get('available')
            change_raw = json_data.get('change')
            recharge = json_data.get('recharge')

            # ── 数字比较用 int 值 ──
            end_time_int = _to_int(end_time_raw)
            response_time_int = _to_int(response_time_raw)
            available = _to_int(available_raw)
            change = _to_int(change_raw)

            if not all([kami_id, end_time_raw, token, statecode, response_time_raw]):
                return {'success': False, 'error': '响应数据缺少必要字段'}
            current_time = int(time.time())
            time_diff = abs(current_time - response_time_int)
            if time_diff > 5:
                return {'success': False, 'error': f'时间戳校验失败，相差{time_diff}秒'}
            date_str = datetime.now().strftime('%Y%m%d%H%M')
            # Token 必须用服务端原始值，不能用转换后的 int
            expected_token = hashlib.md5(f"{kami_id}{self.appkey}{s_original}{end_time_raw}{date_str}".encode()).hexdigest().lower()
            if token.lower() != expected_token:
                return {'success': False, 'error': 'token校验失败'}
            self.statecode = statecode
            self.end_time = end_time_int
            return {
                'success': True,
                'id': kami_id,
                'end_time': end_time_int,
                'amount': json_data.get('amount'),
                'available': available,
                'token': token,
                'statecode': statecode,
                'imei': imei,
                'change': change,
                'core': core,
            }
        except ValueError as e:
            return {'success': False, 'error': str(e)}
        except requests.exceptions.Timeout:
            return {'success': False, 'error': '请求超时'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': '连接错误'}
        except Exception as e:
            return {'success': False, 'error': f'未知错误: {str(e)}'}

    def query_kami(self, kami):
        """查询单码卡密状态信息（不触发登录）"""
        try:
            self._check_init()
            self._check_code(self.query_code, '查询卡密')
            url = self._build_url(self.query_code)
            t = int(time.time())
            post_data = {'kami': kami, 't': t}
            encoded_data, _ = self._encode_params(post_data)
            response = requests.post(url, data=encoded_data, timeout=10)
            try:
                decoded_response = self._decode_response(response.text)
            except Exception as e:
                return {'success': False, 'error': f'响应解码失败: {str(e)}'}
            try:
                json_data = json.loads(decoded_response)
            except:
                return {'success': False, 'error': '响应不是有效的JSON格式'}
            if json_data.get('code') != 200:
                return {'success': False, 'error': json_data.get('msg', '未知错误')}
            return {
                'success': True,
                'state': json_data.get('state'),
                'use': json_data.get('use'),
                'id': json_data.get('id'),
                'use_time': json_data.get('use_time'),
                'end_time': json_data.get('end_time'),
                'line_time': json_data.get('line_time'),
                'line': json_data.get('line'),
                'amount': json_data.get('amount'),
                'available': json_data.get('available'),
            }
        except ValueError as e:
            return {'success': False, 'error': str(e)}
        except requests.exceptions.Timeout:
            return {'success': False, 'error': '请求超时'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': '连接错误'}
        except Exception as e:
            return {'success': False, 'error': f'未知错误: {str(e)}'}

    def heartbeat(self, kami, statecode):
        """单码卡密心跳验证"""
        return self._simple_request(self.heartbeat_code, '单码心跳', {'kami': kami, 'statecode': statecode})

    # ==================== 数据与内容 ====================

    def get_notice(self):
        """获取程序公告"""
        try:
            self._check_init()
            self._check_code(self.notice_code, '公告')
            url = self._build_url(self.notice_code)
            t = int(time.time())
            post_data = {'t': t}
            encoded_data, _ = self._encode_params(post_data)
            response = requests.post(url, data=encoded_data, timeout=10)
            try:
                decoded_response = self._decode_response(response.text)
            except Exception as e:
                return {'success': False, 'error': f'响应解码失败: {str(e)}'}
            try:
                json_data = json.loads(decoded_response)
            except:
                return {'success': False, 'error': '响应不是有效的JSON格式'}
            if json_data.get('code') != 200:
                return {'success': False, 'error': json_data.get('msg', '未知错误')}
            return {'success': True, 'notice': json_data.get('msg', '')}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_latest_version(self):
        """获取最新版本号"""
        try:
            self._check_init()
            self._check_code(self.version_code, '版本号')
            url = self._build_url(self.version_code)
            t = int(time.time())
            post_data = {'t': t}
            encoded_data, _ = self._encode_params(post_data)
            response = requests.post(url, data=encoded_data, timeout=10)
            try:
                decoded_response = self._decode_response(response.text)
            except Exception as e:
                return {'success': False, 'error': f'响应解码失败: {str(e)}'}
            try:
                json_data = json.loads(decoded_response)
            except:
                return {'success': False, 'error': '响应不是有效的JSON格式'}
            if json_data.get('code') != 200:
                return {'success': False, 'error': json_data.get('msg', '未知错误')}
            return {'success': True, 'version': json_data.get('msg', '')}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def check_update(self, ver):
        """检查更新：比较客户端版本号与服务器最新版本"""
        try:
            self._check_init()
            self._check_code(self.check_update_code, '检查更新')
            url = self._build_url(self.check_update_code)
            t = int(time.time())
            post_data = {'ver': ver, 't': t}
            encoded_data, _ = self._encode_params(post_data)
            response = requests.post(url, data=encoded_data, timeout=10)
            try:
                decoded_response = self._decode_response(response.text)
            except Exception as e:
                return {'success': False, 'error': f'响应解码失败: {str(e)}'}
            try:
                json_data = json.loads(decoded_response)
            except:
                return {'success': False, 'error': '响应不是有效的JSON格式'}
            code = json_data.get('code')
            if code == 200:
                return {
                    'success': True,
                    'has_update': True,
                    'ver': json_data.get('ver', ''),
                    'version': json_data.get('version', ''),
                    'uplog': json_data.get('uplog', ''),
                    'upurl': json_data.get('upurl', ''),
                }
            elif code == 201:
                return {'success': True, 'has_update': False, 'msg': json_data.get('msg', '已是最新版')}
            else:
                return {'success': False, 'error': json_data.get('msg', '未知错误')}
        except ValueError as e:
            return {'success': False, 'error': str(e)}
        except requests.exceptions.Timeout:
            return {'success': False, 'error': '请求超时'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': '连接错误'}
        except Exception as e:
            return {'success': False, 'error': f'未知错误: {str(e)}'}

    def get_cloud_doc(self, token):
        """获取云文档内容"""
        result = self._simple_request(self.cloud_doc_code, '云文档', {'token': token})
        if result['success']:
            return {'success': True, 'content': result.get('msg', '')}
        return result

    def app_sign(self, autograph):
        """判断应用签名是否与后台一致"""
        try:
            self._check_init()
            self._check_code(self.app_sign_code, '应用签名')
            url = self._build_url(self.app_sign_code)
            t = int(time.time())
            post_data = {'autograph': autograph, 't': t}
            encoded_data, _ = self._encode_params(post_data)
            response = requests.post(url, data=encoded_data, timeout=10)
            try:
                decoded_response = self._decode_response(response.text)
            except Exception as e:
                return {'success': False, 'error': f'响应解码失败: {str(e)}'}
            try:
                json_data = json.loads(decoded_response)
            except:
                return {'success': False, 'error': '响应不是有效的JSON格式'}
            if json_data.get('code') != 200 and str(json_data.get('code')) != '200':
                return {'success': False, 'error': json_data.get('msg', '未知错误')}
            return {
                'success': True,
                'msg': json_data.get('msg', ''),
                'autograph': json_data.get('autograph', ''),
                'time': json_data.get('time'),
            }
        except ValueError as e:
            return {'success': False, 'error': str(e)}
        except requests.exceptions.Timeout:
            return {'success': False, 'error': '请求超时'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': '连接错误'}
        except Exception as e:
            return {'success': False, 'error': f'未知错误: {str(e)}'}

    # ==================== 用户体系 ====================

    def user_register(self, user, pass_, email=None):
        """用户注册"""
        params = {'user': user, 'pass': pass_}
        if email:
            params['email'] = email
        return self._simple_request(self.register_code, '用户注册', params)

    def user_login(self, user, pass_, imei):
        """用户登录"""
        try:
            self._check_init()
            self._check_code(self.user_login_code, '用户登录')
            url = self._build_url(self.user_login_code)
            t = int(time.time())
            post_data = {'user': user, 'pass': pass_, 'imei': imei, 't': t}
            encoded_data, s_original = self._encode_params(post_data)
            response = requests.post(url, data=encoded_data, timeout=10)
            try:
                decoded_response = self._decode_response(response.text)
            except Exception as e:
                return {'success': False, 'error': f'响应解码失败: {str(e)}'}
            try:
                json_data = json.loads(decoded_response)
            except:
                return {'success': False, 'error': '响应不是有效的JSON格式'}
            if json_data.get('code') != 200:
                return {'success': False, 'error': json_data.get('msg', '未知错误')}
            user_id = json_data.get('id')
            end_time = json_data.get('end_time')
            token = json_data.get('token')
            statecode = json_data.get('statecode')
            self.statecode = statecode
            self.end_time = end_time
            return {
                'success': True,
                'id': user_id,
                'end_time': end_time,
                'statecode': statecode,
                'recharge': json_data.get('recharge'),
                'use_time': json_data.get('use_time'),
                'available': json_data.get('available'),
                'imei': json_data.get('imei'),
                'change': json_data.get('change'),
                'core': json_data.get('core'),
            }
        except ValueError as e:
            return {'success': False, 'error': str(e)}
        except requests.exceptions.Timeout:
            return {'success': False, 'error': '请求超时'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': '连接错误'}
        except Exception as e:
            return {'success': False, 'error': f'未知错误: {str(e)}'}

    def user_heartbeat(self, user, pass_, statecode):
        """用户心跳验证"""
        return self._simple_request(self.user_heartbeat_code, '用户心跳', {'user': user, 'pass': pass_, 'statecode': statecode})

    def qq_login(self, openid, access_token):
        """用户QQ登录"""
        try:
            self._check_init()
            self._check_code(self.qq_login_code, 'QQ登录')
            url = self._build_url(self.qq_login_code)
            t = int(time.time())
            post_data = {'openid': openid, 'access_token': access_token, 't': t}
            encoded_data, s_original = self._encode_params(post_data)
            response = requests.post(url, data=encoded_data, timeout=10)
            try:
                decoded_response = self._decode_response(response.text)
            except Exception as e:
                return {'success': False, 'error': f'响应解码失败: {str(e)}'}
            try:
                json_data = json.loads(decoded_response)
            except:
                return {'success': False, 'error': '响应不是有效的JSON格式'}
            if json_data.get('code') != 200:
                return {'success': False, 'error': json_data.get('msg', '未知错误')}
            self.statecode = json_data.get('statecode')
            self.end_time = json_data.get('end_time')
            return {
                'success': True,
                'id': json_data.get('id'),
                'end_time': json_data.get('end_time'),
                'statecode': json_data.get('statecode'),
                'recharge': json_data.get('recharge'),
                'use_time': json_data.get('use_time'),
                'available': json_data.get('available'),
                'change': json_data.get('change'),
                'core': json_data.get('core'),
            }
        except ValueError as e:
            return {'success': False, 'error': str(e)}
        except requests.exceptions.Timeout:
            return {'success': False, 'error': '请求超时'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': '连接错误'}
        except Exception as e:
            return {'success': False, 'error': f'未知错误: {str(e)}'}

    def bind_qq(self, user, pass_, openid, access_token):
        """用户绑定QQ"""
        return self._simple_request(self.bind_qq_code, '绑定QQ', {'user': user, 'pass': pass_, 'openid': openid, 'access_token': access_token})

    def change_password(self, user, oldpass, newpass):
        """用户修改密码"""
        return self._simple_request(self.change_password_code, '修改密码', {'user': user, 'oldpass': oldpass, 'newpass': newpass})

    def user_cancel(self, user, pass_):
        """用户注销账号"""
        return self._simple_request(self.user_cancel_code, '用户注销', {'user': user, 'pass': pass_})

    def recharge(self, user, card):
        """用户充值卡密"""
        return self._simple_request(self.recharge_code, '用户充值', {'user': user, 'card': card})

    # ==================== 设备与安全 ====================

    def unbind_kami(self, kami, imei):
        """单码卡密解绑设备"""
        return self._simple_request(self.unbind_code, '解绑设备', {'kami': kami, 'imei': imei})

    def unbind_user(self, user, pass_, imei):
        """用户账号解绑设备"""
        return self._simple_request(self.unbind_code, '解绑设备', {'user': user, 'pass': pass_, 'imei': imei})

    def ip_unbind_kami(self, kami):
        """单码卡密 IP 解绑"""
        return self._simple_request(self.ip_unbind_code, 'IP解绑', {'kami': kami})

    def ip_unbind_user(self, user, pass_):
        """用户账号 IP 解绑"""
        return self._simple_request(self.ip_unbind_code, 'IP解绑', {'user': user, 'pass': pass_})

    def disable_kami(self, kami):
        """禁用单码卡密"""
        return self._simple_request(self.disable_code, '禁用', {'kami': kami})

    def disable_user(self, user, pass_):
        """禁用用户账号"""
        return self._simple_request(self.disable_code, '禁用', {'user': user, 'pass': pass_})

    # ==================== 远程变量 ====================

    def get_variable_by_kami(self, kami, valueid, valuename):
        """通过卡密获取远程变量"""
        result = self._simple_request(self.get_variable_code, '获取变量',
                                       {'kami': kami, 'valueid': valueid, 'valuename': valuename})
        if result['success']:
            return {'success': True, 'value': result.get('msg', '')}
        return result

    def get_variable_by_user(self, user, pass_, valueid, valuename):
        """通过用户获取远程变量"""
        result = self._simple_request(self.get_variable_code, '获取变量',
                                       {'user': user, 'pass': pass_, 'valueid': valueid, 'valuename': valuename})
        if result['success']:
            return {'success': True, 'value': result.get('msg', '')}
        return result

    def modify_variable_by_kami(self, kami, valueid, valuecontent):
        """通过卡密修改远程变量"""
        return self._simple_request(self.modify_variable_code, '修改变量',
                                     {'kami': kami, 'valueid': valueid, 'valuecontent': valuecontent})

    def modify_variable_by_user(self, user, pass_, valueid, valuecontent):
        """通过用户修改远程变量"""
        return self._simple_request(self.modify_variable_code, '修改变量',
                                     {'user': user, 'pass': pass_, 'valueid': valueid, 'valuecontent': valuecontent})

    # ==================== 核心数据 ====================

    def modify_core_by_kami(self, kami, core):
        """通过卡密修改核心数据"""
        return self._simple_request(self.modify_core_code, '修改核心数据', {'kami': kami, 'core': core})

    def modify_core_by_user(self, user, pass_, core):
        """通过用户修改核心数据"""
        return self._simple_request(self.modify_core_code, '修改核心数据', {'user': user, 'pass': pass_, 'core': core})

    def get_core_by_kami(self, kami):
        """获取卡密核心数据"""
        result = self._simple_request(self.get_kami_core_code, '获取卡密核心数据', {'kami': kami})
        if result['success']:
            return {'success': True, 'core': result.get('msg', '')}
        return result

    def get_core_by_user(self, user, pass_):
        """获取用户核心数据"""
        result = self._simple_request(self.get_user_core_code, '获取用户核心数据', {'user': user, 'pass': pass_})
        if result['success']:
            return {'success': True, 'core': result.get('msg', '')}
        return result

    # ==================== 在线数量 ====================

    def get_online_kami_count(self):
        """获取当前在线卡密数量"""
        result = self._simple_request(self.online_kami_code, '获取在线卡密数量', {})
        if result['success']:
            return {'success': True, 'count': int(result.get('msg', '0'))}
        return result

    def get_online_user_count(self):
        """获取当前在线用户数量"""
        result = self._simple_request(self.online_user_code, '获取在线用户数量', {})
        if result['success']:
            return {'success': True, 'count': int(result.get('msg', '0'))}
        return result
