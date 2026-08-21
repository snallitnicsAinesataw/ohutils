import random
import requests
from ..core.config import Config, getGlobalConfig
from ..core.util import Comment, BlogEntry, getVersion, APIError, mergeBlogData
from typing import List, Dict, Tuple, TypeVar
from ..core.blog_api import getAllBlogComments, getBlogRaw
from ..core.exception import BIDError
import struct
import zlib
import time
import os
from datetime import datetime
from deprecated import deprecated
CURR_LATEST_OBARC_VER = 5
_T = TypeVar('_T')


def parseComment2(data: bytes, offset: int) -> tuple[Comment, int]:
    bcid, uid, ts, content_len = struct.unpack_from('<III I', data, offset)
    offset += 16
    content = data[offset:offset + content_len].decode('utf-8')
    offset += content_len
    reply_count = data[offset]
    offset += 1
    replies = []
    for _ in range(reply_count):
        reply, offset = parseComment2(data, offset)
        replies.append(reply)
    return Comment[BlogEntry](bcid, uid, ts, content, reply_count, replies, False, 0, 'blog'), offset


def parseComment3(data: bytes, offset: int) -> tuple[Comment, int]:
    bcid, uid, ts, content_len = struct.unpack_from('<III I', data, offset)
    offset += 16
    content = data[offset:offset + content_len].decode('utf-8')
    offset += content_len
    reply_count = struct.unpack_from('<I', data, offset)[0]
    offset += 4
    replies = []
    for _ in range(reply_count):
        reply, offset = parseComment3(data, offset)
        replies.append(reply)
    return Comment[BlogEntry](bcid, uid, ts, content, reply_count, replies, False, 0, 'blog'), offset


def parseComment4(data: bytes, offset: int) -> tuple[Comment, int]:
    """v4评论格式与v3一致，可以直接使用parseComment3"""
    return parseComment3(data, offset)


def parseComment5(data: bytes, offset: int) -> tuple[Comment, int]:
    bcid, uid, ts, pin, content_len = struct.unpack_from('<IIII I', data, offset)
    offset += 20
    content = data[offset:offset + content_len].decode('utf-8')
    offset += content_len
    reply_count = struct.unpack_from('<I', data, offset)[0]
    offset += 4
    replies = []
    for _ in range(reply_count):
        reply, offset = parseComment5(data, offset)
        replies.append(reply)
    return Comment[BlogEntry](bcid, uid, ts, content, reply_count, replies, bool(pin), pin, 'blog'), offset


def parseBlog2(data: bytes, offset: int, channel_id: int, timestamp: int, arc_time: int) -> tuple[BlogEntry, int]:
    (bid, uid, like, fav, view, title_len) = struct.unpack_from('<II HHHH', data, offset)
    offset += 16  # 4+4+2+2+2+2
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
        comment, offset = parseComment2(data, offset)
        comments.append(comment)
    return BlogEntry(bid, uid, like, fav, view, channel_id, title, timestamp, arc_time, content, comments), offset


def parseBlog3(data: bytes, offset: int, channel_id: int, pub_ts: int, arc_ts: int) -> tuple[BlogEntry, int]:
    bid, uid, like, fav, view, title_len = struct.unpack_from('<II HHHH', data, offset)
    offset += 16

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
        c, offset = parseComment3(data, offset)
        comments.append(c)

    return BlogEntry(bid, uid, like, fav, view, channel_id, title, pub_ts, arc_ts, content, comments), offset


def parseBlog4(data: bytes, flags: int,
               offset: int, channel_id: int, pub_ts: int, arc_ts: int, tag_count: int) -> tuple[BlogEntry, int]:
    bid, uid, like, fav, view = struct.unpack_from('<II HHH', data, offset)
    offset += 14

    is_gore = bool(flags & 2)
    tags = []
    for _ in range(tag_count):
        tag_len = struct.unpack_from('<H', data, offset)[0]
        offset += 2
        tag = data[offset: offset + tag_len].decode('utf-8')
        offset += tag_len
        tags.append(tag)

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
        c, offset = parseComment3(data, offset)
        comments.append(c)

    return BlogEntry(bid, uid, like, fav, view, channel_id, title, pub_ts, arc_ts, content, comments,
                     b_type, tags, cr_type, is_gore, attached_vid), offset


def parseBlog5(data: bytes, flags: int,
               offset: int, channel_id: int, pub_ts: int, arc_ts: int, tag_count: int) -> tuple[BlogEntry, int]:
    bid, uid, like, fav, view = struct.unpack_from('<II HHH', data, offset)
    offset += 14

    is_gore = bool(flags & 2)
    tags = []
    for _ in range(tag_count):
        tag_len = struct.unpack_from('<H', data, offset)[0]
        offset += 2
        tag = data[offset: offset + tag_len].decode('utf-8')
        offset += tag_len
        tags.append(tag)

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
        c, offset = parseComment5(data, offset)
        comments.append(c)

    return BlogEntry(bid, uid, like, fav, view, channel_id, title, pub_ts, arc_ts, content, comments,
                     b_type, tags, cr_type, is_gore, attached_vid), offset


def _writeObarc(version: int, bid: int, blog_data: dict, comments: List[Comment], config: Config = None):
    """写入单个动态的.obarc文件"""
    if config is None:
        config = getGlobalConfig()

    filename = os.path.join(config.savePath, config.fileName.format(bid=bid))
    with open(filename, "wb") as f:
        # 文件头 (32字节)
        pub_ts = int(datetime.strptime(blog_data.get("time", "2000-1-1 00:00:00"), "%Y-%m-%d %H:%M:%S").timestamp())
        archive_ts = int(time.time())
        channel_id = blog_data.get("channel_id", 0)
        if version >= 4:
            cr_type = blog_data.get("copyright_type", 0)
            b_type = blog_data.get("blog_type", 0)
            attached_vid = blog_data.get("attached_vid", 0)
            tags = blog_data.get("tag", [])
            flag = blog_data.get("is_gore", 0) << 1

        f.write(b'OBARC')  # 4B magic
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

        # 动态条目
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

        f.write(struct.pack('<H', len(title_bytes)))  # title_len
        f.write(title_bytes)  # title
        f.write(struct.pack('<I', len(content_bytes)))  # content_len
        f.write(content_bytes)  # content
        f.write(struct.pack('<H', len(comments)))  # comment_count

        # 递归写评论
        def write_comment(c):
            content_bytes = c.content.encode('utf-8')
            f.write(struct.pack('<I', c.cid))
            f.write(struct.pack('<I', c.uid))
            f.write(struct.pack('<I', c.timestamp))
            if version == 5:  # v5新增字段pin_order
                f.write(struct.pack('<I', c.pin_order))
            f.write(struct.pack('<I', len(content_bytes)))
            f.write(content_bytes)
            if version == 2:
                f.write(struct.pack('<B', len(c.replies)))
            elif version >= 3:
                f.write(struct.pack('<I', len(c.replies)))
                # v3及之后将reply_count改为4字节
            for reply in c.replies:
                write_comment(reply)

        for comment in comments:
            write_comment(comment)

        # 结尾标记
        end_marker = bytes.fromhex("DC BD CC B2 A0 AD B9 B7 F0 A8 DC BF B5 C4 A8 E8 DC B7")
        f.write(end_marker)
        file_size = f.tell()

    with open(filename, "r+b") as f:
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
        print(f"[_writeObarc]Write complete in v{version}: {filename}, CRC32: {crc32:08X}")
    return filename


@deprecated(reason="为向后兼容保留，请使用writeObarc()", version='0.5.0')
def writeObarc2(bid: int, blog_data: dict, comments: List[Comment], config: Config = None):
    return _writeObarc(2, bid, blog_data, comments, config)


@deprecated(reason="为向后兼容保留，请使用writeObarc()", version='0.5.0')
def writeObarc3(bid: int, blog_data: dict, comments: List[Comment], config: Config = None):
    return _writeObarc(3, bid, blog_data, comments, config)


@deprecated(reason="为向后兼容保留，请使用writeObarc()", version='0.5.0')
def writeObarc4(bid: int, blog_data: dict, comments: List[Comment], config: Config = None):
    return _writeObarc(4, bid, blog_data, comments, config)


def writeObarc(bid: int, blog_data: dict, comments: List[Comment], config: Config = None):
    """写入单篇动态的.obarc文件，使用最新的.obarc版本。"""
    return _writeObarc(CURR_LATEST_OBARC_VER, bid, blog_data, comments, config)


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
        if not data.endswith(bytes.fromhex("DCBDCCB2A0ADB9B7F0A8DCBFB5C4A8E8DCB7")):
            return False, f"wrong file end marker"
        return True, "OK"


def _loadObarc(version: int, bid: int, config: Config = None) -> BlogEntry:
    if config is None:
        config = getGlobalConfig()
    with open(os.path.join(config.savePath, config.fileName.format(bid=bid)), "rb") as f:
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

    if version == 2:
        blog, _ = parseBlog2(data, 0, channel_id, timestamp, archive_time)
    elif version == 3:
        blog, _ = parseBlog3(data, 0, channel_id, timestamp, archive_time)
    elif version == 4:
        blog, _ = parseBlog4(data, flags, 0, channel_id, timestamp, archive_time, tag_count)
    else:
        blog, _ = parseBlog5(data, flags, 0, channel_id, timestamp, archive_time, tag_count)
    return blog


@deprecated(reason="为向后兼容保留，请使用loadObarc()", version='0.5.0')
def loadObarc2(bid: int, config: Config = None) -> BlogEntry:
    return _loadObarc(2, bid, config)


@deprecated(reason="为向后兼容保留，请使用loadObarc()", version='0.5.0')
def loadObarc3(bid: int, config: Config = None) -> BlogEntry:
    return _loadObarc(3, bid, config)


@deprecated(reason="为向后兼容保留，请使用loadObarc()", version='0.5.0')
def loadObarc4(bid: int, config: Config = None) -> BlogEntry:
    return _loadObarc(4, bid, config)


def loadObarc(bid: int, config: Config = None) -> BlogEntry:
    """从config.savePath中加载.obarc文件。"""
    if config is None:
        config = getGlobalConfig()
    filename = os.path.join(config.savePath, config.fileName.format(bid=bid))
    ver = getVersion(filename)
    return _loadObarc(ver, bid, config)


def loadObarcBytes(f_bytes: bytes) -> BlogEntry:
    header = f_bytes[:32]
    version = header[5]
    flags = header[6]
    tag_count = header[0x1E]
    # 提取channel_id (偏移0x1C, 2字节)
    channel_id = struct.unpack('<H', header[0x1C:0x1E])[0]
    timestamp = struct.unpack('<I', header[0x8:0xC])[0]
    archive_time = struct.unpack('<I', header[0xC:0x10])[0]
    if version == 5:
        blog, _ = parseBlog5(f_bytes[32:], flags, 0, channel_id, timestamp, archive_time, tag_count)
    elif version == 4:
        blog, _ = parseBlog4(f_bytes[32:], flags, 0, channel_id, timestamp, archive_time, tag_count)
    elif version == 3:
        blog, _ = parseBlog3(f_bytes[32:], 0, channel_id, timestamp, archive_time)
    else:
        blog, _ = parseBlog2(f_bytes[32:], 0, channel_id, timestamp, archive_time)
    return blog


def _archiveBlog(version: int, bid: int, config: Config = None) -> Tuple[str, bool]:
    """Override policy: keep(不动原存档), override(覆盖), merge(混合新数据与原数据) """
    if config is None:
        config = getGlobalConfig()

    file_name = config.fileName.format(bid=bid)
    file_path = os.path.join(config.savePath, file_name)
    verbose = config.verbose
    policy = config.policy

    if policy not in ['keep', 'merge', 'override']:
        raise ValueError
    if os.path.exists(file_path):
        if policy == 'keep':
            if verbose:
                print(f"[_archiveBlog/v{version}]{config.colorYellow}File {file_name} already exist, skip due to 'keep' policy\033[0m")
            return file_path, False

    if verbose:
        print(f"[_archiveBlog/v{version}]Get bid ob{bid}...")
    blog_data, comments = {}, []  # 默认值。在26/8/9左右修复了仍能获取已删除动态评论的bug。这是坏事。
    try:
        blog_data = getBlogRaw(bid)
    except BIDError as e:
        if verbose:
            print(f"[_archiveBlog/v{version}]{config.colorRed}Blog ob{bid} content get failed: {e}\033[0m")
    else:
        time.sleep(random.uniform(*config.blogToCommentDelay))
        if verbose:
            print(f"[_archiveBlog/v{version}]Get comments of ob{bid}...")
        try:
            comments = getAllBlogComments(bid)
        except requests.RequestException as e:
            if verbose:
                print(f'[_archiveBlog/v{version}]{config.colorRed}Network error: {e}\033[0m')
            return file_path, True
        if verbose:
            print(f"[_archiveBlog/v{version}]Finish, get {len(comments)} top comment(s) in total")

    if not os.path.exists(file_path) or policy == 'override':
        return _writeObarc(version, bid, blog_data, comments, config), True

    if policy == 'merge':
        if verbose:
            print(f"[_archiveBlog/v{version}]{config.colorYellow}File {file_name} already exist, start to merge due to 'merge' policy\033[0m")

        ver = getVersion(os.path.join(config.savePath, config.fileName.format(bid=bid)))
        old_blog = _loadObarc(ver, bid, config)
        merged_blog = mergeBlogData(old_blog, blog_data)
        merged_comments = mergeComments(old_blog.comments, comments)
        file_name = _writeObarc(version, bid, merged_blog, merged_comments, config)
        if verbose:
            print(f"[_archiveBlog/v{version}]File {file_name} merge complete")
    return file_path, True


@deprecated(reason="为向后兼容保留，请使用archiveBlog()", version='0.5.0')
def archiveBlog2(bid: int, config: Config = None) -> Tuple[str, bool]:
    return _archiveBlog(2, bid, config)


@deprecated(reason="为向后兼容保留，请使用archiveBlog()", version='0.5.0')
def archiveBlog3(bid: int, config: Config = None) -> Tuple[str, bool]:
    return _archiveBlog(3, bid, config)


@deprecated(reason="为向后兼容保留，请使用archiveBlog()", version='0.5.0')
def archiveBlog4(bid: int, config: Config = None) -> Tuple[str, bool]:
    return _archiveBlog(4, bid, config)


def archiveBlog(bid: int, config: Config = None) -> Tuple[str, bool]:
    """存储动态至.obarc文件。
    config.policy: keep(不动原存档), override(覆盖), merge(混合新数据与原数据)"""
    return _archiveBlog(CURR_LATEST_OBARC_VER, bid, config)
