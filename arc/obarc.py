import random
import requests
from ..core.config import Config, getGlobalConfig
from ..core.util import (
    Comment, BlogEntry, getVersion, APIError, decrypt, genKey, logger, parseTime, formatTime,
    _format, _fn_formatTime, _c)
from typing import List, Dict, Tuple, TypeVar, Optional
from ..core.blog_api import getAllBlogComments, getBlogDetail
from ..core.exception import BIDError
from ..core._const import _LATEST_OBARC_VER, DEFAULT_TS, _OBARC_END_MARKER, _YELLOW, _RED
import struct
import zlib
import time
import os
import hashlib
from datetime import datetime
_T = TypeVar('_T')


def _parseComment(c_type: Literal['blog', 'video', 'seiga'], version: int, data: bytes, offset: int) -> tuple[Comment, int]:
    pin = 0  # PyCharm别扯
    if version >= 5:
        bcid, uid, ts, pin, content_len = struct.unpack_from('<IIII I', data, offset)
        offset += 20
    else:
        bcid, uid, ts, content_len = struct.unpack_from('<III I', data, offset)
        offset += 16
    content = data[offset:offset + content_len].decode('utf-8')
    offset += content_len
    if version >= 3:
        reply_count = struct.unpack_from('<I', data, offset)[0]
        offset += 4
    else:
        reply_count = data[offset]
        offset += 1
    replies = []
    for _ in range(reply_count):
        reply, offset = _parseComment(c_type, version, data, offset)
        replies.append(reply)
    if version >= 5:
        return Comment(bcid, uid, ts, content, reply_count, replies, bool(pin), pin, c_type), offset
    else:
        return Comment(bcid, uid, ts, content, reply_count, replies, False, 0, c_type), offset


def _parseBlog(version: int, data: bytes, flags: int, offset: int, channel_id: int,
               pub_ts: int, arc_ts: int, tag_count: int, pswd: bytes = b'') -> tuple[BlogEntry, int]:
    b_type, tags, cr_type, is_gore, attached_vid, forward_bid, is_unavailable = 0, [], 0, False, 0, 0, False
    # PyCharm别扯
    if version <= 3:
        bid, uid, like, fav, view, title_len = struct.unpack_from('<II HHHH', data, offset)
        offset += 16
    else:
        # ver >= 4
        # 为.obarc支持F_ENCRYPT_CONTENT作准备。
        is_gore = flags & 2
        is_unavailable = flags & 4
        is_encrypted = flags & 1
        if is_encrypted:
            salt = data[offset: offset + 16]
            offset += 16
            key, _ = genKey(pswd, salt)
            data = decrypt(key, data[offset:])
            offset = 0

        bid, uid, like, fav, view = struct.unpack_from('<II HHH', data, offset)
        offset += 14

        tags = []
        for _ in range(tag_count):
            tag_len = struct.unpack_from('<H', data, offset)[0]
            offset += 2
            tag = data[offset: offset+tag_len].decode('utf-8')
            offset += tag_len
            tags.append(tag)

        if version >= 6:
            attached_vid, cr_type, b_type, forward_bid, title_len = struct.unpack_from('<IIII H', data, offset)
            offset += 18
        else:
            attached_vid, cr_type, b_type, title_len = struct.unpack_from('<III H', data, offset)
            offset += 14

    title = data[offset:offset + title_len].decode('utf-8')
    offset += title_len

    content_len = struct.unpack_from('<I', data, offset)[0]
    offset += 4
    content = data[offset:offset + content_len].decode('utf-8')
    offset += content_len

    comment_count = struct.unpack_from('<H', data, offset)[0]
    offset += 2

    comments = []
    for _ in range(comment_count):
        c, offset = _parseComment('blog', version, data, offset)
        comments.append(c)
    if version >= 6:
        return BlogEntry(bid, uid, like, fav, view, channel_id, title, pub_ts, arc_ts, content, comments,
                         b_type, tags, cr_type, is_gore, attached_vid, forward_bid, is_unavailable), offset
    elif 4 <= version <= 5:
        return BlogEntry(bid, uid, like, fav, view, channel_id, title, pub_ts, arc_ts, content, comments,
                         b_type, tags, cr_type, is_gore, attached_vid), offset
    else:
        return BlogEntry(bid, uid, like, fav, view, channel_id, title, pub_ts, arc_ts, content, comments), offset


def _writeComment(comment_ver: int, f, comment: Comment):
    # 递归写评论
    content_bytes = comment.content.encode('utf-8')
    f.write(struct.pack('<I', comment.cid))
    f.write(struct.pack('<I', comment.uid))
    f.write(struct.pack('<I', comment.timestamp))
    if comment_ver >= 5:  # v5新增字段pin_order
        f.write(struct.pack('<I', comment.pin_order))
    f.write(struct.pack('<I', len(content_bytes)))
    f.write(content_bytes)
    if comment_ver == 2:
        f.write(struct.pack('<B', len(comment.replies)))
    elif comment_ver >= 3:
        f.write(struct.pack('<I', len(comment.replies)))
        # v3及之后将reply_count改为4字节
    for reply in comment.replies:
        _writeComment(comment_ver, f, reply)


def _writeObarc(version: int, bid: int, blog_data: dict, comments: List[Comment], fp: str, config: Config = None):
    """写入单个动态的.obarc文件。"""
    if config is None:
        config = getGlobalConfig()

    with open(fp, "wb") as f:
        # ===================文件头 (32字节)===================
        pub_ts = parseTime(blog_data["time"]) if blog_data.get("time") else DEFAULT_TS
        archive_ts = int(time.time())
        channel_id = blog_data.get("channel_id", 0)
        if version >= 4:
            cr_type = blog_data.get("copyright_type", 0)
            b_type = blog_data.get("blog_type", 0)
            attached_vid = blog_data.get("attached_vid", 0)
            tags = blog_data.get("tag", [])
            forward = blog_data.get("forward")
            is_unavailable = 0
            if forward is not None:
                is_unavailable = forward.get("is_unavailable")
            flag = (blog_data.get("is_gore", 0) << 1) | is_unavailable << 2

        f.write(b'OBARC')  # 5B magic
        f.write(struct.pack('<B', version))  # 1B版本
        f.write(struct.pack('<B', flag if version == 4 else 0))  # 1B 标志位
        f.write(struct.pack('<B', 0))  # 1B 保留
        f.write(struct.pack('<I', pub_ts))  # 4B 原始发布时间
        f.write(struct.pack('<I', archive_ts))  # 4B 存档时间
        f.write(struct.pack('<Q', 0))  # 8B 总大小（占位）
        f.write(struct.pack('<I', 0))  # 4B CRC32（占位）
        f.write(struct.pack('<H', channel_id))  # 2B 频道ID
        f.write(struct.pack('<B', len(tags) if version >= 4 else 0))  # 1B 保留 / tag数量(仅v4)
        f.write(b'\xA5')  # 1B 头结尾

        # ===================动态条目===================
        title_bytes = blog_data.get("title", "").encode('utf-8')
        content_bytes = blog_data.get("content", "").encode('utf-8')
        f.write(struct.pack('<I', int(blog_data.get("bid", bid))))  # bid
        f.write(struct.pack('<I', int(blog_data.get("uid", 0))))  # uid
        f.write(struct.pack('<H', int(blog_data.get("like_count", 0))))  # like
        f.write(struct.pack('<H', int(blog_data.get("favorite_count", 0))))  # fav
        f.write(struct.pack('<H', int(blog_data.get("view_count", 0))))  # view

        # v4新增字段
        if version >= 4:
            for t in tags:
                t_bytes = t.encode('utf-8')
                f.write(struct.pack('<H', len(t_bytes)))
                f.write(t_bytes)
            f.write(struct.pack('<I', int(attached_vid)))
            f.write(struct.pack('<I', int(cr_type)))
            f.write(struct.pack('<I', int(b_type)))
            if version >= 6:
                # v6新增字段
                f.write(struct.pack('<I', blog_data.get("forward_bid", 0)))

        f.write(struct.pack('<H', len(title_bytes)))  # title_len
        f.write(title_bytes)  # title
        f.write(struct.pack('<I', len(content_bytes)))  # content_len
        f.write(content_bytes)  # content
        f.write(struct.pack('<H', len(comments)))  # comment_count

        for comment in comments:
            _writeComment(version, f, comment)

        # ===================结尾标记===================
        f.write(_OBARC_END_MARKER)
        file_size = f.tell()

    with open(fp, "r+b") as f:
        # CRC32和总大小回填
        f.seek(0x20)
        all_data = f.read()
        crc32 = zlib.crc32(all_data) & 0xFFFFFFFF  # 计算 CRC32

        # 回填总大小(偏移0x10)
        f.seek(0x10)
        f.write(struct.pack('<Q', file_size))

        # 回填CRC32(偏移0x18)
        f.seek(0x18)
        f.write(struct.pack('<I', crc32))

    if config.verbose:
        logger.info(f"[_writeObarc/v{version}]Write complete: {fp}, CRC32: {crc32:08X}")
    return fp


def mergeComments(old_list: List[Comment[_T]], new_list: List[Comment[_T]]) -> List[Comment[_T]]:
    """合并两个评论列表，适用于更新数据。"""
    old_dict = {c.cid: c for c in old_list}
    new_dict = {c.cid: c for c in new_list}
    all_bcids = set(old_dict.keys()) | set(new_dict.keys())

    merged = []
    for bcid in all_bcids:
        if bcid in old_dict and bcid in new_dict:
            merged.append(mergeCommentsDeep(old_dict[bcid], new_dict[bcid]))
        elif bcid in new_dict:
            merged.append(new_dict[bcid])
        else:
            merged.append(old_dict[bcid])

    merged.sort(key=lambda c: c.timestamp)
    return merged


def mergeCommentsDeep(old: Comment[_T], new: Comment[_T]) -> Comment[_T]:
    """递归合并两条评论(cid相同)。"""
    if old.cid != new.cid:
        raise ValueError("cid不匹配")
    # 使用新评论的元数据
    merged = Comment(
        cid=new.cid,
        uid=new.uid,
        timestamp=new.timestamp,
        content=new.content,
        reply_count=new.reply_count,
        replies=[],
        is_pinned=new.is_pinned,
        pin_order=new.pin_order,
        c_type=new.c_type
    )

    # 递归合并子回复
    old_replies = {r.cid: r for r in old.replies}
    new_replies = {r.cid: r for r in new.replies}
    all_bcids = set(old_replies.keys()) | set(new_replies.keys())

    for bcid in all_bcids:
        if bcid in old_replies and bcid in new_replies:
            # 两边都有 -> 递归合并
            merged_reply = mergeCommentsDeep(old_replies[bcid], new_replies[bcid])
            merged.replies.append(merged_reply)
        elif bcid in new_replies:
            # 只有新有 -> 直接添加
            merged.replies.append(new_replies[bcid])
        else:
            # 只有旧有 -> 保留旧的
            merged.replies.append(old_replies[bcid])

    # 按bcid或时间排序
    merged.replies.sort(key=lambda r: r.timestamp)
    return merged


def verifyObarc(filepath: str):
    """验证指定路径的.obarc文件是否合法。"""
    with open(filepath, "rb") as f:
        # 读文件头
        header = f.read(32)
        if header[:5] != b'OBARC':
            return False, "wrong magic"
        if header[0x1F] != 0xA5:
            return False, "wrong header end marker"
        stored_crc = struct.unpack('<I', header[0x18:0x1C])[0]
        stored_size = struct.unpack('<Q', header[0x10:0x18])[0]
        # 读取数据部分 (从0x20开始到文件尾)
        data = f.read()
        calc_crc = zlib.crc32(data) & 0xFFFFFFFF
        if calc_crc != stored_crc:
            return False, f"wrong CRC32: stored {stored_crc:08X}, calc {calc_crc:08X}"
        # 检查文件大小
        f.seek(0, 2)
        actual_size = f.tell()
        if actual_size != stored_size:
            return False, f"wrong size: stored {stored_size}, actual {actual_size}"
        if not data.endswith(_OBARC_END_MARKER):
            return False, f"wrong file end marker"
        return True, "OK"


def _loadObarc(version: int, fp: str) -> BlogEntry:
    flags, tag_count = 0, 0
    with open(fp, "rb") as f:
        header = f.read(32)
        # 提取channel_id (偏移0x1C, 2字节)
        if version >= 4:
            flags = struct.unpack('<B', header[6:7])[0]
        channel_id = struct.unpack('<H', header[0x1C:0x1E])[0]
        timestamp = struct.unpack('<I', header[0x8:0xC])[0]
        archive_time = struct.unpack('<I', header[0xC:0x10])[0]
        if version >= 4:
            tag_count = struct.unpack('<B', header[0x1E:0x1F])[0]
        # 跳过文件头，读取数据部分
        data = f.read()

    blog, _ = _parseBlog(version, data, flags, 0, channel_id, timestamp, archive_time, tag_count)
    return blog


def loadBlog(bid: int, fn: str = None, config: Config = None) -> BlogEntry:
    """从config.savePath中加载.obarc文件。
    若savePath中包含了除了{bid}之外的占位符，应提供完整文件名。此时bid参数被忽略。"""
    if config is None:
        config = getGlobalConfig()
    if fn is None:
        try:
            fn = _format(config.fileName, bid="ob%i" % bid) + '.obarc'
        except KeyError as e:
            raise ValueError(
                f"fileName包含bid以外的占位符{e}") from e
    filepath = os.path.join(config.savePath, fn)
    ver = getVersion(filepath)
    return _loadObarc(ver, filepath)


def loadBlogBytes(f_bytes: bytes) -> BlogEntry:
    header = f_bytes[:32]
    version = header[5]
    flags = header[6]
    tag_count = header[0x1E]
    # 提取channel_id (偏移0x1C, 2字节)
    channel_id = struct.unpack('<H', header[0x1C:0x1E])[0]
    timestamp = struct.unpack('<I', header[0x8:0xC])[0]
    archive_time = struct.unpack('<I', header[0xC:0x10])[0]
    blog, _ = _parseBlog(version, f_bytes[32:], flags, 0, channel_id, timestamp, archive_time, tag_count)
    return blog


def _archiveBlog(version: int, bid: int, config: Config = None) -> Tuple[Optional[str], bool]:
    if config is None:
        config = getGlobalConfig()

    verbose = config.verbose
    policy = config.policy

    if policy not in ['keep', 'merge', 'override', 'keep_after']:
        raise ValueError
    if policy == 'keep':
        if '{pubts}' in config.fileName or '{pubftime}' in config.fileName:
            raise ValueError(
                "keep策略仅支持{bid}、{ver}、{toolver}占位符，请用keep_after")
        keep_fn = _format(config.fileName, bid='ob%i' % bid, ver=version) + '.obarc'
        file_path = os.path.join(config.savePath, keep_fn)
        if os.path.exists(file_path):
            if verbose:
                t_ = f"File {keep_fn} already exist, skip due to 'keep' policy"
                logger.info(f"[_archiveBlog/v{version}]{_c(_YELLOW, t_, config)}")
            return file_path, False

    # ===================获取动态正文===================
    if verbose:
        logger.info(f"[_archiveBlog/v{version}]Get bid ob{bid}...")
    try:
        blog_data = getBlogDetail(bid, config=config)
        pub_ts = parseTime(blog_data["time"]) if blog_data.get("time") else DEFAULT_TS
        fn = _format(
            config.fileName,
            bid='ob%i' % bid, uid=blog_data.get('uid', 0),
            ver=version,
            pubts=pub_ts,
            pubftime=_fn_formatTime(pub_ts),
        ) + '.obarc'
        file_path = os.path.join(config.savePath, fn)
    except BIDError as e:
        t_ = f"Blog ob{bid} content get failed: {e}"
        logger.error(f"[_archiveBlog/v{version}]{_c(_RED, t_, config)}")
        return None, True  # 在26/8/9左右修复了仍能获取已删除动态评论的bug。这是坏事。

    # ===================获取评论===================
    time.sleep(random.uniform(*config.blogToCommentDelay))
    if verbose:
        logger.info(f"[_archiveBlog/v{version}]Get comments of ob{bid}...")
    try:
        comments = getAllBlogComments(bid, config=config)
    except requests.RequestException as e:
        t_ = f"Network error: {e}"
        logger.error(f'[_archiveBlog/v{version}]{_c(_RED, t_, config)}')
        return file_path, True
    if verbose:
        logger.info(f"[_archiveBlog/v{version}]Finish, get {len(comments)} top comment(s) in total")

    # ===================写文件===================
    exist = os.path.exists(file_path)
    if not exist or policy == 'override':
        return _writeObarc(version, bid, blog_data, comments, file_path, config=config), True

    if policy == 'keep_after':
        if verbose:
            t_ = f"File {fn} already exist, discard data due to 'keep_after' policy"
            logger.info(
                f"[_archiveBlog/v{version}]{_c(_YELLOW, t_, config)}")
        return file_path, True

    if policy == 'merge':
        t_ = f"File {fn} already exist, start to merge due to 'merge' policy"
        if verbose:
            logger.info(f"[_archiveBlog/v{version}]{_c(_YELLOW, t_, config)}")

        ver = getVersion(file_path)
        old_blog = _loadObarc(ver, file_path)
        # 内联的_mergeBlogData。
        merged_blog = {
                'bid': int(blog_data.get('bid', old_blog.bid)),
                'uid': int(blog_data.get('uid', old_blog.uid)),
                'like_count': int(blog_data.get('like_count', old_blog.like_count)),
                'favorite_count': int(blog_data.get('favorite_count', old_blog.favorite_count)),
                'view_count': int(blog_data.get('view_count', old_blog.view_count)),
                'channel_id': int(blog_data.get('channel_id', old_blog.channel_id)),
                'time': blog_data.get('time', "2000-1-1 00:00:00"),
                'title': blog_data.get('title', old_blog.title),
                'content': blog_data.get('content', old_blog.content),
                'blog_type': int(blog_data.get('blog_type', old_blog.blog_type)),
                'tags': list(set(old_blog.tags + blog_data.get('tags', []))),
                'copyright_type': int(blog_data.get('copyright_type', old_blog.copyright_type)),
                'is_gore': bool(blog_data.get('is_gore', old_blog.is_gore)),
                'attached_vid': int(blog_data.get('attached_vid', old_blog.attached_vid))
            }
        merged_comments = mergeComments(old_blog.comments, comments)
        file_name = _writeObarc(version, bid, merged_blog, merged_comments, file_path, config=config)
        if verbose:
            logger.info(f"[_archiveBlog/v{version}]File {file_name} merge complete")
    return file_path, True


def saveBlog(bid: int, config: Config = None) -> Tuple[str, bool]:
    """存储动态至.obarc文件。"""
    return _archiveBlog(_LATEST_OBARC_VER, bid, config)
