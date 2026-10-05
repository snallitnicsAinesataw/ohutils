from __future__ import annotations
import random
from dataclasses import dataclass, field, fields, asdict
from datetime import datetime
from typing import TypeVar, Generic, List, Union, Literal, Callable, Optional, Generator
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
from .config import Config, getGlobalConfig, setGlobalConfig, _getIConfig
from contextlib import contextmanager
from .exception import APIError, mappings, MethodNotAllowed, ExhaustedRetriesError
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import logging
from requests import Response
from . import _const
import string
import io

_TParent = TypeVar('_TParent', bound=Union['VideoEntry', 'BlogEntry'])
_T = TypeVar('_T')
logger = logging.getLogger(__name__)


@dataclass
class Comment(Generic[_TParent]):
    cid: int
    uid: int
    timestamp: int
    content: str
    reply_count: int
    replies: List['Comment[_TParent]']
    is_pinned: bool
    pin_order: int
    c_type: Literal['blog', 'video', 'seiga']
    parent_cid: int = 0


@dataclass
class Danmaku:
    danmaku_id: int
    text: str
    time_ms: int
    mode: Literal['top', 'bottom', 'scroll']
    color_rgb: int
    font_size: int
    render: str


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
    tags: list[str] = field(default_factory=list)
    copyright_type: int = 0
    is_gore: bool = False
    attached_vid: int = 0
    forward_bid: int = 0
    is_unavailable: bool = False

    def toDict(self):
        return asdict(self)

    def toDictShallow(self):
        """不转换comments: list[Comment[BlogEntry]] -> list[dict]。"""
        return {f.name: getattr(self, f.name) for f in fields(self)}


@dataclass
class Staff:
    uid: int
    role: str
    sort_order: int


@dataclass
class VideoEntry:
    vid: int
    uid: int
    like_count: int
    favorite_count: int
    view_count: int
    duration: int
    channel_id: int
    pub_time: int
    arc_time: int
    tags: list[str]
    vid_type: int
    category: int
    title: str
    intro: str
    staffs: list[Staff]
    danmaku: list[Danmaku] = field(repr=False)
    comments: list[Comment['VideoEntry']]
    is_gore: bool

    _cover: bytes = field(repr=False)  # 封面二进制
    _video_fp: str  # .ovarc路径
    _video_offset: int  # video在文件里的偏移
    _video_size: int  # video字节数

    def extractCover(self) -> bytes:
        return self._cover

    def _extractVideo(self, chunk_size: int = 8192):
        with open(self._video_fp, 'rb') as f:
            f.seek(self._video_offset)
            remaining = self._video_size
            while remaining > 0:
                chunk = f.read(min(chunk_size, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    def extractVideo(self, fp: str = None, chunk_size: int = 8192) -> Optional[Generator[bytes, None, None]]:
        """提取视频。提供fp以保存至文件。"""
        if fp is None:
            return self._extractVideo(chunk_size)
        else:
            with open(fp, 'wb') as f:
                for chunk in self._extractVideo(chunk_size):
                    f.write(chunk)


def parseTime(time_str: str) -> int:
    """YYYY-MM-DD HH:MM:SS -> Unix时间戳。"""
    return int(datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").timestamp())


def formatTime(ts: int) -> str:
    """Unix时间戳 -> YYYY-MM-DD HH:MM:SS。"""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _c(color: str, str_, c: Config):
    return color + str(str_) + _const._CLEAR if c.richLog else str_


def startEnd(func_=None, *, is_auth: bool = False):
    """装饰器。"""
    def deco(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取参数绑定
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # 格式化参数为 {key=value} 形式
            params = bound_args.arguments
            config = params.get('config') or getGlobalConfig()
            # print('****debug: verbose =',config.verbose)

            if not config.useStartEnd or is_auth:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception:
                    raise

            else:
                if config.verbose:
                    args_str = ', '.join([f"{k}={v}" for k, v in params.items()]).replace('\n', '\\n')
                    cutted = args_str[:25]
                    t_ = f"with args {cutted}{'...' if cutted != args_str else ''}"
                    logger.debug(f"[{func.__name__}]start {_c(_const._GRAY, t_, config)}")
                else:
                    logger.debug(f"[{func.__name__}]start")
                try:
                    result = func(*args, **kwargs)
                    if config.verbose:
                        result_str = str(result).replace('\n', '\\n')
                        cutted = result_str[:25]
                        t_ = f"with return {cutted}{'...' if result_str != cutted else ''}"
                        logger.debug(f"[{func.__name__}]end {_c(_const._GRAY, t_, config)}")
                    else:
                        logger.debug(f"[{func.__name__}]end")
                    return result
                except Exception:
                    if config.verbose:
                        exc_type, exc_value, _ = sys.exc_info()
                        t_ = f"with exception {exc_type.__name__}({exc_value})"
                        logger.debug(f"[{func.__name__}]end {_c(_const._RED, t_, config)}")
                    raise
        return wrapper

    if func_ is None:
        return deco
    return deco(func_)


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


def dict2BlogComment(d: dict) -> Comment:
    """此函数支持嵌套replies的转换。"""
    return Comment(
        cid=d['bcid'],
        uid=d['uid'],
        timestamp=d['timestamp'],
        content=d['content'],
        reply_count=d['reply_count'],
        replies=[dict2BlogComment(reply) for reply in d.get('replies', [])],
        is_pinned=bool(d['is_pinned']),
        pin_order=bool(d['pin_order']),
        c_type='blog'
    )


def getVersion(path: str) -> int:
    """获取文件的版本号。"""
    with open(path, "rb") as f:
        f.read(5)  # 魔数头
        return f.read(1)[0]  # 版本号


def _raise_exhaust(retries, url, f_name, config):
    t_ = f"Retries({retries}) exhausted while requesting {url.split('token=')[0].strip('&?')}"
    raise ExhaustedRetriesError(f"[{f_name}]{_c(_const._RED, t_, config)}")


def _request(method: Literal['get', 'post', 'put', 'delete'], return_type: Literal['json', 'content', 'stream'],
             f_name: str, url: str, *, config: Config = None, data = None,
             is_long: bool = False, is_chat: bool = False, chat_token: str = None, stream: bool = False,
             files: dict = None, no_retry: bool = False, is_video: bool = False, is_form: bool = False,
             content_type: str = None
             ) -> Union[dict, bytes, Response]:
    if config is None:
        config = getGlobalConfig()
    retries = 1 if no_retry else config.retries
    method, return_type = method.lower(), return_type.lower()
    timeout = config.longTimeout if is_long else config.timeout

    if config.alwaysUseToken and not is_chat:
        # is_chat=True时此配置无效
        parsed = urlparse(url)
        query: dict[str, List[str]] = parse_qs(parsed.query)  # noqa, PyCharm别扯
        query['token'] = [config.token]
        new_query = urlencode(query, doseq=True)
        url = urlunparse(parsed._replace(query=new_query))

    for attempt in range(retries):
        try:
            if isinstance(data, io.IOBase) and attempt > 0:
                try:
                    data.seek(0)
                except (OSError, io.UnsupportedOperation):
                    # 不可seek且重试 -> 重试牛魔
                    raise
            if config.verbose:
                t_url = url.split('token=')[0].strip('&?')
                t_cutted = t_url[:100]
                logger.info(f"[{f_name}]{method} {_c(_const._GRAY, t_cutted + ('...' if t_cutted != t_url else ''), config)}")

            headers = dict(config.headers)
            headers.setdefault('User-Agent', 'OHUtils/0.9.0')   # 水印，大概
            if is_video:
                headers['Range'] = 'bytes=0-'
            if chat_token is not None:
                headers['Authorization'] = 'Bearer ' + chat_token
            if content_type is not None:
                headers['Content-Type'] = content_type
            if files and content_type is None:
                headers.pop('Content-Type', None)  # 交给requests自己生成boundary

            if method == 'get':
                resp = requests.get(url, timeout=timeout, headers=headers, stream=stream)
            elif method == 'post' and not files:
                if is_form:
                    resp = requests.post(url, timeout=timeout, headers=headers, data=data)
                else:
                    resp = requests.post(url, timeout=timeout, headers=headers, json=data)
            elif method == 'post' and files:
                resp = requests.post(url, timeout=timeout, headers=headers, files=files, data=data)
            elif method == 'put':
                if is_form:
                    resp = requests.put(url, timeout=timeout, headers=headers, data=data)
                else:
                    resp = requests.put(url, timeout=timeout, headers=headers, json=data)
            elif method == 'delete':
                resp = requests.delete(url, timeout=timeout, headers=headers, json=data)
            else:
                raise ValueError('不支持的method: ' + method)
            resp.raise_for_status()

            if return_type == 'stream' or stream:
                return resp
            elif return_type == 'json':
                jsoned = resp.json()
                stat, msg = jsoned.get("status"), jsoned.get('message')
                if stat != "success":
                    raise mappings.get(msg, APIError)(msg)
                if isinstance(jsoned, dict):
                    jsoned.pop('status', None)
                return jsoned
            elif return_type == 'content':
                return resp.content

        except requests.HTTPError as e:
            # 发生HTTP错误
            status = e.response.status_code
            try:
                jsoned = e.response.json()
                stat, msg = jsoned.get("status"), jsoned.get('message')
                if stat != "success":
                    raise mappings.get(msg, APIError)(msg)
            except ValueError:
                # 如果响应不是JSON
                if status >= 500:
                    # 5xx，重试
                    if attempt == retries - 1:
                        _raise_exhaust(retries, url, f_name, config)  # 耗尽，raise
                    t_ = f"Retry {attempt + 1}/{retries}: {e}"
                    logger.warning(f"[{f_name}]{_c(_const._YELLOW, t_, config)}")
                    time.sleep(random.uniform(*config.retryDelay))
                    continue
                # 4xx不重试
                t_ = f"{e.response.status_code} error: {e.response.text}"
                raise APIError(f"[{f_name}]{_c(_const._RED, t_, config)}")
        except (requests.RequestException, ValueError) as e:
            if attempt == retries - 1:
                _raise_exhaust(retries, url, f_name, config)  # 耗尽，raise
            t_ = f"Retry {attempt + 1}/{retries}: {e}"
            logger.warning(f"[{f_name}]{_c(_const._YELLOW, t_, config)}")
            time.sleep(random.uniform(*config.retryDelay))

    _raise_exhaust(retries, url, f_name, config)  # 末尾raise


def flattenComments(recur_list: list[Comment[_T]]) -> list[Comment[_T]]:
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


@contextmanager
def appSim(config: Config = None):
    """模拟由STCaoMei(ou5558)开发的OTTOHub App。不能嵌套。"""
    if config is None:
        config = getGlobalConfig()

    original = config
    sim_config = config.copy()
    sim_config.headers = config.headers.copy()
    sim_config.headers['User-Agent'] = 'Dart/3.12 (dart:io)'
    sim_config.alwaysUseToken = True

    ic = _getIConfig()
    setGlobalConfig(sim_config)
    ic.config_occupied = True
    try:
        yield sim_config
    finally:
        ic.config_occupied = False
        setGlobalConfig(original)


@contextmanager
def useConfig(config: Config):
    """使用给定的config。不能嵌套。
    此函数的优先级低于在函数调用时显式传递的config=...参数，但高于setGlobalConfig(...)。"""
    orig_cfg = getGlobalConfig()
    setGlobalConfig(config)
    _getIConfig().config_occupied = True
    try:
        yield config
    finally:
        _getIConfig().config_occupied = False
        setGlobalConfig(orig_cfg)  # 恢复配置


def _recur_request(f_name: str, recur_func: Callable[[int], tuple[list[_T], Optional[int]]],
                   limit: int, delay: tuple[float, float], *, is_page: bool = False, config: Config = None) -> list[_T]:
    """recur_func: (off) -> (items, total_items|None)
    is_page=True时off是page, 否则是offset。"""
    if config is None:
        config = getGlobalConfig()
    all_ = []
    off_page = 1 if is_page else 0
    while True:
        if off_page != 0 and config.verbose:
            logger.info(f"[{f_name}]curr offset/page: {off_page}")
        try:
            items, total = recur_func(off_page)
        except ExhaustedRetriesError as e:
            logger.error(f"[{f_name}]{_c(_RED, f'fail to get all: {e}', config)}")
            if all_:
                logger.warning(f"[{f_name}]{_c(_YELLOW, f'end prematurely, already got {len(all_)} item(s)', config)}")
            break
        if not items:
            if all_:
                logger.warning(f"[{f_name}]{_c(_YELLOW, f'end prematurely(empty page), already got {len(all_)} item(s)', config)}")
            break
        all_.extend(items)
        if total is not None:
            if len(all_) >= total:
                break
        elif len(items) < limit:
            break
        if is_page:
            off_page += 1
        else:
            off_page += limit
        time.sleep(random.uniform(*delay))
    return all_


def _format(pattern: str, **k):
    return pattern.format(
        bid=k.get('bid', 'ob0'), sid=k.get('sid', 0), vid=k.get('vid', 0), m_id=k.get('m_id', 0),
        ext=k.get('ext', ''), ver=k.get('ver', '0'), toolver=_const._version,

        # 请求后才可以知道的字段
        uid=k.get('uid', 0),
        page=k.get('page', 0),
        dur=k.get('dur', 0),
        durf=k.get('durf', '000000'),
        pubftime=k.get('pubftime', _const._DEFAULT_FN_TIME),
        pubts=k.get('pubts', _const.DEFAULT_TS),
        filesize=k.get('filesize', 0)
        # crc32='{crc32}',
        # sha1='{sha1}',
    )


def _temp_name(name: str) -> str:
    rand = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{name}.{rand}.ohu-temp"


def _fn_formatTime(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y%m%d_%H%M%S")


def _fn_2hms(dur: int) -> str:
    h, rem = divmod(dur, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m{s:02d}s"


def _iter_chunks(stream, chunk_size=8192):
    if isinstance(stream, bytes):
        for i in range(0, len(stream), chunk_size):
            yield stream[i:i + chunk_size]
    else:  # Response
        for chunk_ in stream.iter_content(chunk_size):
            if chunk_: yield chunk_


def _tag_factory(tags: list[str]) -> str:
    try:
        tags.remove('吉吉国民')
    except ValueError:
        pass
    return "#" + "#".join(str(t) for t in tags)
