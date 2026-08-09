from dataclasses import dataclass, field, fields, asdict
from datetime import datetime
from typing import List
import inspect
import os
import sys
import requests
import time
from functools import wraps
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.exceptions import InvalidTag
from .config import Config, getGlobalConfig, setGlobalConfig
from contextlib import contextmanager
from .exceptions import APIError, mappings


@dataclass
class Comment:
    bcid: int
    uid: int
    timestamp: int
    content: str
    reply_count: int
    replies: List['Comment']

    @classmethod
    def fromDict(cls, d: dict):
        """从字典导入
        replies会保留为list[dict]，可以使用dict2Comment(...)"""
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class Danmaku:
    danmaku_id: int
    text: str
    time: float
    mode: str
    color: str
    font_size: str
    render: str

    @classmethod
    def fromDict(cls, d: dict):
        """从字典导入"""
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class BlogEntry:
    bid: int
    uid: int
    like_count: int
    favorite_count: int
    view_count: int
    channel_id: int
    title: str
    timestamp: int
    arc_time: int
    content: str
    comments: List[Comment]

    blog_type: int = 0
    tags: List[str] = field(default_factory=list)
    copyright_type: int = 0
    is_gore: bool = False
    attached_vid: int = 0

    def toDict(self):
        return asdict(self)


@dataclass
class VideoEntry:
    vid: int
    uid: int
    like_count: int
    favorite_count: int
    view_count: int
    channel_id: int
    timestamp: int
    tags: List[str]
    vid_type: int
    category: int
    title: str
    intro: str
    danmaku: List[Danmaku]
    comment_count: int
    comments: List[Comment]

    @classmethod
    def fromDict(cls, d: dict):
        """从字典更新配置"""
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**filtered)


def parseTime(time_str: str) -> int:
    """YYYY-MM-DD HH:MM:SS -> Unix timestamp"""
    return int(datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").timestamp())


def formatTime(ts: int) -> str:
    """Unix timestamp -> YYYY-MM-DD HH:MM:SS"""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def startEnd(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 获取参数绑定
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # 格式化参数为 {key=value} 形式
        params = bound_args.arguments
        config = params.get('config') or getGlobalConfig()
        # print("[debug/se]", func.__name__, params)

        if config.noStartEnd:
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                raise

        else:
            if config.verbose:
                args_str = ', '.join([f"{k}={v}" for k, v in params.items()]).replace('\n', '\\n')
                cutted = args_str[:25]
                print(f"[{config.colorGray}SE:\033[0m{func.__name__}]"
                      f"start {config.colorGray}with args {cutted}{'...' if cutted!=args_str else ''}\033[0m")
            else:
                print(f"[{config.colorGray}SE:\033[0m{func.__name__}]start")
            try:
                result = func(*args, **kwargs)
                if config.verbose:
                    result_str = str(result).replace('\n', '\\n')
                    cutted = result_str[:25]
                    print(
                        f"[{config.colorGray}SE:\033[0m{func.__name__}]"
                        f"end {config.colorGray}with return {cutted}{'...' if result_str != cutted else ''}\033[0m"
                    )
                else:
                    print(f"{config.colorGray}SE:\033[0m[{func.__name__}]end")
                return result
            except Exception:
                if config.verbose:
                    exc_type, exc_value, _ = sys.exc_info()
                    print(
                        f"[{config.colorGray}SE:\033[0m{func.__name__}]"
                        f"end {config.colorRed}with exception {exc_type.__name__}({exc_value}{config.colorRed})\033[0m")
                raise

    return wrapper


def genKey(pswd: bytes, salt: bytes = None) -> bytes:
    if salt is None:
        salt = os.urandom(16)
    return PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 32 bytes for AES-256
        salt=salt,
        iterations=100000,
    ).derive(pswd)


def encrypt(key: bytes, plaintext: bytes) -> bytes:
    """encryption using aes256(GCM)."""
    iv = os.urandom(12)
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    ciphertext = iv + encryptor.tag + ciphertext
    return ciphertext


def decrypt(key: bytes, ciphertext: bytes) -> bytes:
    """decryption using aes256(GCM)."""
    iv = ciphertext[:12]
    tag = ciphertext[12:28]
    actual_ciphertext = ciphertext[28:]
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
    decrypt_ = cipher.decryptor()
    plaintext = decrypt_.update(actual_ciphertext) + decrypt_.finalize()
    return plaintext


def dict2Comment(d: dict) -> Comment:
    """此函数支持嵌套replies的转换"""
    return Comment(
        bcid=d['bcid'],
        uid=d['uid'],
        timestamp=d['timestamp'],
        content=d['content'],
        reply_count=d['reply_count'],
        replies=[dict2Comment(reply) for reply in d.get('replies', [])]
    )


def getVersion(path: str) -> int:
    with open(path, "rb") as f:
        f.read(5)  # OBARC
        return f.read(1)[0]  # 版本号


def _requestJson(f_name: str, url: str, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    retries = config.retries
    for attempt in range(retries):
        try:
            if config.verbose:
                print(f"[{f_name}]get{config.colorGray} {url.split('token=')[0].strip('&?')}\033[0m")
            resp = requests.get(url, timeout=config.timeout, headers=config.headers)
            resp.raise_for_status()
            jsoned = resp.json()
            stat, msg = jsoned.get("status"), jsoned.get('message')
            if stat != "success":
                raise mappings.get(msg, APIError)(msg)
            return jsoned
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                try:
                    jsoned = e.response.json()
                    stat, msg = jsoned.get("status"), jsoned.get('message')
                    if stat != "success":
                        raise mappings.get(msg, APIError)(msg)
                except ValueError:
                    # 如果响应不是 JSON
                    raise APIError(f"[{f_name}]{config.colorRed}400 error: {e.response.text}")
        except (requests.RequestException, ValueError) as e:
            if attempt == retries - 1:
                raise
            if config.verbose:
                print(f"[{f_name}]{config.colorYellow}Retry {attempt + 1}/{retries}: {e}\033[0m")
            time.sleep(0.5 * (attempt + 1))

    return {}  # dummy


def _requestContent(f_name: str, url: str, config: Config = None) -> bytes:
    if config is None:
        config = getGlobalConfig()
    retries = config.retries
    for attempt in range(retries):
        try:
            if config.verbose:
                print(f"[{f_name}]get{config.colorGray} {url.split('token=')[0].strip('&?')}\033[0m")
            resp = requests.get(url, timeout=config.timeout, headers=config.headers)
            resp.raise_for_status()
            return resp.content
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                try:
                    jsoned = e.response.json()
                    stat, msg = jsoned.get("status"), jsoned.get('message')
                    if stat != "success":
                        raise mappings.get(msg, APIError)(msg)
                except ValueError:
                    # 如果响应不是 JSON
                    raise APIError(f"[{f_name}]{Config.colorRed}400 error: {e.response.text}")
        except (requests.RequestException, ValueError) as e:
            if attempt == retries - 1:
                raise
            if config.verbose:
                print(f"[{f_name}]{config.colorYellow}Retry {attempt + 1}/{retries}: {e}\033[0m")
            time.sleep(0.5 * (attempt + 1))
    return b''  # dummy


def _postJson(f_name: str, url: str, data: dict, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    retries = config.retries
    for attempt in range(retries):
        try:
            if config.verbose:
                print(f"[{f_name}]post{config.colorGray} {url.split('token=')[0].strip('&?')}\033[0m")
            resp = requests.post(url, json=data, timeout=config.timeout, headers=config.headers)
            resp.raise_for_status()
            jsoned = resp.json()
            stat, msg = jsoned.get("status"), jsoned.get('message')
            if stat != "success":
                raise mappings.get(msg, APIError)(msg)
            return jsoned
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                try:
                    jsoned = e.response.json()
                    stat, msg = jsoned.get("status"), jsoned.get('message')
                    if stat != "success":
                        raise mappings.get(msg, APIError)(msg)
                except ValueError:
                    # 如果响应不是 JSON
                    raise APIError(f"[{f_name}]{Config.colorRed}400 error: {e.response.text}")
        except (requests.RequestException, ValueError) as e:
            if attempt == retries - 1:
                raise
            if config.verbose:
                print(f"[{f_name}]{config.colorYellow}Retry {attempt + 1}/{retries}: {e}\033[0m")
            time.sleep(0.5 * (attempt + 1))
    return {}  # dummy


def flattenComments(recur_list: list[Comment]) -> list[Comment]:
    res = []
    for c in recur_list:
        res.append(c)
        if c.replies:
            res.extend(flattenComments(c.replies))
    return res


def mergeBlogEntry(old: BlogEntry, new: BlogEntry) -> BlogEntry:
    """合并两个 BlogEntry"""
    return BlogEntry(
        bid=new.bid,
        uid=new.uid,
        like_count=new.like_count,
        favorite_count=new.favorite_count,
        view_count=new.view_count,
        channel_id=new.channel_id,
        timestamp=new.timestamp,
        arc_time=new.arc_time,
        title=new.title,
        content=new.content,
        comments=mergeComments(old.comments, new.comments),
        blog_type=old.blog_type or new.blog_type,
        tags=list(set(old.tags + new.tags)),  # 合并标签
        copyright_type=old.copyright_type or new.copyright_type,
        is_gore=old.is_gore or new.is_gore,
        attached_vid=old.attached_vid or new.attached_vid
    )


def mergeBlogData(old: BlogEntry, new: dict) -> dict:
    """合并新旧数据，writeObarc的专用函数
    我服了"""
    return {
        'bid': int(new.get('bid', old.bid)),
        'uid': int(new.get('uid', old.uid)),
        'like_count': int(new.get('like_count', old.like_count)),
        'favorite_count': int(new.get('favorite_count', old.favorite_count)),
        'view_count': int(new.get('view_count', old.view_count)),
        'channel_id': int(new.get('channel_id', old.channel_id)),
        'time': new.get('time', "2000-1-1 00:00:00"),
        'title': new.get('title', old.title),
        'content': new.get('content', old.content),
        'blog_type': int(new.get('blog_type', old.blog_type)),
        'tags': list(set(old.tags + new.get('tags', []))),
        'copyright_type': int(new.get('copyright_type', old.copyright_type)),
        'is_gore': bool(new.get('is_gore', old.is_gore)),
        'attached_vid': int(new.get('attached_vid', old.attached_vid))
    }


@contextmanager
def appSim(config: Config = None):
    if config is None:
        config = getGlobalConfig()
    # 保存原始配置
    orig_headers = config.headers.copy()
    orig_token = config.alwaysUseToken
    # 应用模拟配置
    config.headers['User-Agent'] = 'Dart/3.12 (dart:io)'
    config.alwaysUseToken = True
    setGlobalConfig(config)
    try:
        yield config
    finally:
        # 恢复配置
        config.headers = orig_headers
        config.alwaysUseToken = orig_token
