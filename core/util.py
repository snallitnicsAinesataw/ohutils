from __future__ import annotations
import random
from dataclasses import dataclass, field, fields, asdict
from datetime import datetime
from typing import TypeVar, Generic, List, Union, Literal
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
from .exception import APIError, mappings, MethodNotAllowed, ExhaustedRetriesError
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


_T = TypeVar('_T', bound=Union['VideoEntry', 'BlogEntry'])


@dataclass
class Comment(Generic[_T]):
    cid: int
    uid: int
    timestamp: int
    content: str
    reply_count: int
    replies: List['Comment[_T]']
    is_pinned: bool
    pin_order: int
    c_type: Literal['blog', 'video']
    parent_cid: int = 0


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
        """从字典导入。"""
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
    comments: List[Comment['BlogEntry']]

    blog_type: int = 0
    tags: List[str] = field(default_factory=list)
    copyright_type: int = 0
    is_gore: bool = False
    attached_vid: int = 0

    def toDict(self):
        return asdict(self)

    def toDictShallow(self):
        """不转换comments: list[Comment[BlogEntry]] -> list[dict]。"""
        return {f.name: getattr(self, f.name) for f in fields(self)}


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
    comments: List[Comment['VideoEntry']]

    @classmethod
    def fromDict(cls, d: dict):
        """从字典更新配置。"""
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**filtered)


def parseTime(time_str: str) -> int:
    """YYYY-MM-DD HH:MM:SS -> Unix时间戳。"""
    return int(datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").timestamp())


def formatTime(ts: int) -> str:
    """Unix时间戳 -> YYYY-MM-DD HH:MM:SS。"""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def startEnd(func):
    """装饰器。"""
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
                      f"start {config.colorGray}with args {cutted}{'...' if cutted != args_str else ''}\033[0m")
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
                    print(f"[{config.colorGray}SE:\033[0m{func.__name__}]end")
                return result
            except Exception:
                if config.verbose:
                    exc_type, exc_value, _ = sys.exc_info()
                    print(
                        f"[{config.colorGray}SE:\033[0m{func.__name__}]"
                        f"end {config.colorRed}with exception {exc_type.__name__}({exc_value}{config.colorRed})\033[0m")
                raise

    return wrapper


def genKey(pswd: bytes, salt: bytes = None) -> tuple[bytes, bytes]:
    """使用给定的密码和盐生成密钥。若salt未给出(None)则使用随机盐值。
    返回(key, salt)。"""
    if salt is None:
        salt = os.urandom(16)
    return PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 32 bytes for AES-256
        salt=salt,
        iterations=100000,
    ).derive(pswd), salt


def encrypt(key: bytes, plaintext: bytes) -> bytes:
    """使用AES256(GCM)的加密函数。"""
    iv = os.urandom(12)
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    ciphertext = iv + encryptor.tag + ciphertext
    return ciphertext


def decrypt(key: bytes, ciphertext: bytes) -> bytes:
    """使用AES256(GCM)的解密函数。"""
    iv = ciphertext[:12]
    tag = ciphertext[12:28]
    actual_ciphertext = ciphertext[28:]
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
    decrypt_ = cipher.decryptor()
    plaintext = decrypt_.update(actual_ciphertext) + decrypt_.finalize()
    return plaintext


def blogDict2Comment(d: dict) -> Comment:
    """此函数支持嵌套replies的转换。"""
    return Comment(
        cid=d['bcid'],
        uid=d['uid'],
        timestamp=d['timestamp'],
        content=d['content'],
        reply_count=d['reply_count'],
        replies=[blogDict2Comment(reply) for reply in d.get('replies', [])],
        is_pinned=bool(d['is_pinned']),
        pin_order=bool(d['pin_order']),
        c_type='blog'
    )


def getVersion(path: str) -> int:
    """获取文件的版本号。"""
    with open(path, "rb") as f:
        f.read(5)  # 魔数头
        return f.read(1)[0]  # 版本号


def _request(method: Literal['get', 'post', 'put', 'delete'], return_type: Literal['json', 'content'],
             f_name: str, url: str, config: Config = None, data: dict = None,
             is_long: bool = False, is_chat: bool = False, chat_token: str = None
             ) -> Union[dict, bytes]:
    if config is None:
        config = getGlobalConfig()
    retries = config.retries
    method, return_type = method.lower(), return_type.lower()
    timeout = config.uploadTimeout if is_long else config.timeout
    for attempt in range(retries):
        try:
            if config.alwaysUseToken and not is_chat:
                # is_chat=True时此配置无效
                parsed = urlparse(url)
                query: dict[str, List[str]] = parse_qs(parsed.query)  # noqa, PyCharm别扯
                query['token'] = [config.token]
                new_query = urlencode(query, doseq=True)
                url = urlunparse(parsed._replace(query=new_query))
            if config.verbose:
                print(f"[{f_name}]{method}{config.colorGray} {url.split('token=')[0].strip('&?')}\033[0m")
            headers = config.headers
            headers['User-Agent'] = headers['User-Agent']  # + ' OHUtils/0.6.0'  # 水印，大概
            if chat_token is not None:
                headers['Authorization'] = 'Bearer ' + chat_token
            if method == 'get':
                resp = requests.get(url, timeout=timeout, headers=headers)
            elif method == 'post':
                resp = requests.post(url, timeout=timeout, headers=headers, json=data)
            elif method == 'put':
                resp = requests.put(url, timeout=timeout, headers=headers, data=data)
            elif method == 'delete':
                resp = requests.delete(url, timeout=timeout, headers=headers)
            else:
                raise MethodNotAllowed
            resp.raise_for_status()
            if return_type == 'json':
                jsoned = resp.json()
                stat, msg = jsoned.get("status"), jsoned.get('message')
                if stat != "success":
                    raise mappings.get(msg, APIError)(msg)
                return jsoned
            elif return_type == 'content':
                return resp.content
        except requests.HTTPError as e:
            try:
                jsoned = e.response.json()
                stat, msg = jsoned.get("status"), jsoned.get('message')
                if stat != "success":
                    raise mappings.get(msg, APIError)(msg)
            except ValueError:
                # 如果响应不是JSON
                raise APIError(f"[{f_name}]{config.colorRed}{e.response.status_code} error: {e.response.text}")
        except (requests.RequestException, ValueError) as e:
            if attempt == retries - 1:
                raise ExhaustedRetriesError(
                    f"[{f_name}]{config.colorRed}Retries({retries}) exhausted "
                    f"while requesting {url.split('token=')[0].strip('&?')}\033[0m")
            if config.verbose:
                print(f"[{f_name}]{config.colorYellow}Retry {attempt + 1}/{retries}: {e}\033[0m")
            time.sleep(random.uniform(*config.retryDelay))
    raise ExhaustedRetriesError(
        f"[{f_name}]{config.colorRed}Retries({retries}) exhausted "
        f"while requesting {url.split('token=')[0].strip('&?')}\033[0m")


def flattenComments(recur_list: list[Comment]) -> list[Comment]:
    """将评论树展平。"""
    res = []
    for c in recur_list:
        res.append(c)
        if c.replies:
            flat = flattenComments(c.replies)
            for rc in flat:
                rc.parent_cid = c.cid
            res.extend(flat)
    return res


def mergeBlogEntry(old: BlogEntry, new: BlogEntry) -> BlogEntry:
    """合并两个BlogEntry。"""
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
    """合并新旧数据，writeObarc的专用函数。
    我服了。别用这个。"""
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
    """模拟由STCaoMei(ou5558)开发的OTTOHub App。"""
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


@contextmanager
def useConfig(config: Config):
    """使用给定的config。
    此函数的优先级低于在函数调用时显式传递的config=...参数，但高于setGlobalConfig(...)。"""
    orig_cfg = getGlobalConfig()
    setGlobalConfig(config)
    try:
        yield config
    finally:
        setGlobalConfig(orig_cfg)  # 恢复配置
