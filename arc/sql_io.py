import sqlite3
import os
from typing import Union, Any
from time import time
from ..core.config import Config, getGlobalConfig
from ..core.util import parseTime, _request, startEnd, BlogEntry, flattenComments, Comment, VideoEntry
from dataclasses import asdict, dataclass
from enum import IntEnum


def _tag_factory(tags: list[str]) -> str:
    try:
        tags.remove('吉吉国民')
    except ValueError:
        pass
    return ','.join(tags)


class _MT(IntEnum):
    # 因为记不住。
    UNKNOWN = 0
    USER = 1
    BLOG = 2
    M_OBC_API = 3
    M_BLOG_ENTRY = 4
    OBC = 5
    OVC = 6
    OSC = 7
    M_OSC_API = 8
    FOLLOW = 9
    BLOG_COLL = 10
    VIDEO_COLL = 11
    SEIGA_COLL = 12
    SEIGA = 13
    SEIGA_TAG = 14
    SEIGA_TAGMAP = 15
    SEIGA_PAGE = 16
    VIDEO = 17
    MEDIA = 18
    CHANNEL = 19
    CHANNEL_SECTION = 20
    CHANNEL_NOTICE = 21


@dataclass(frozen=True)
class _SQLBatch:
    sql_type: _MT
    data: Any


#########################################################################################
# {sql_type: int -> tuple[table_name: str, table_def: str, prim_key: str]}
_MAP = {
    _MT.USER: ('oh_user_v1', '''uid INTEGER PRIMARY KEY NOT NULL, name TEXT, intro TEXT, create_ts INTEGER,
        sex TEXT, honour TEXT, exp INTEGER, avatar BLOB, cover_h BLOB, cover_v BLOB, video INTEGER, blog INTEGER,
        seiga INTEGER, media INTEGER, follow INTEGER, fan INTEGER, avatar_url TEXT, cover_h_url TEXT, cover_v_url TEXT,
        CHECK (((avatar IS NULL AND avatar_url IS NOT NULL) OR (avatar IS NOT NULL AND avatar_url IS NULL)) AND 
        ((cover_h IS NULL AND cover_h_url IS NOT NULL) OR (cover_h IS NOT NULL AND cover_h_url IS NULL)) AND 
        ((cover_v IS NULL AND cover_v_url IS NOT NULL) OR (cover_v IS NOT NULL AND cover_v_url IS NULL)))''', 'uid'),
    _MT.BLOG: ('oh_blog_v1', '''bid INTEGER PRIMARY KEY NOT NULL, uid INTEGER, pub_ts INTEGER, arc_ts INTEGER,
        channel INTEGER, like INTEGER, fav INTEGER, view INTEGER, attached_vid INTEGER, copyright_type INTEGER,
        blog_type INTEGER, comment_count INTEGER, title TEXT, content TEXT, tags TEXT, gore INTEGER, forward_bid INTEGER,
        forward_died INTEGER''', 'bid'),
    _MT.OBC: ('oh_obc_v1', '''bcid INTEGER PRIMARY KEY NOT NULL, bid INTEGER, uid INTEGER, parent_bcid INTEGER DEFAULT 0,
        pub_ts INTEGER, arc_ts INTEGER, content TEXT, reply_count INTEGER DEFAULT 0, pin_order INTEGER DEFAULT 0''',
              'bcid'),
    _MT.OVC: ('oh_ovc_v1', '''vcid INTEGER PRIMARY KEY NOT NULL, vid INTEGER, uid INTEGER, parent_vcid INTEGER DEFAULT 0,
        pub_ts INTEGER, arc_ts INTEGER, content TEXT, reply_count INTEGER DEFAULT 0, pin_order INTEGER DEFAULT 0''',
              'vcid'),
    _MT.OSC: ('oh_osc_v1', '''scid INTEGER PRIMARY KEY NOT NULL, sid INTEGER, uid INTEGER, parent_scid INTEGER DEFAULT 0, 
        pub_ts INTEGER, arc_ts INTEGER, content TEXT, reply_count INTEGER DEFAULT 0, pin_order INTEGER DEFAULT 0''',
              'scid'),
    _MT.FOLLOW: ('oh_follow_v1', 'uid INTEGER, target_uid INTEGER, PRIMARY KEY (uid, target_uid)', '(uid, target_uid)'),
    _MT.BLOG_COLL: ('oh_blog_collection_v1', '''bid INTEGER NOT NULL, uid INTEGER, name TEXT NOT NULL, 
        sort_order INTEGER, arc_ts INTEGER, PRIMARY KEY (name, bid)''', '(name, bid)'),
    _MT.VIDEO_COLL: ('oh_video_collection_v1', '''vid INTEGER NOT NULL, uid INTEGER, name TEXT NOT NULL, 
        sort_order INTEGER, arc_ts INTEGER, PRIMARY KEY (name, vid)''', '(name, vid)'),
    _MT.SEIGA_COLL: ('oh_seiga_collection_v1', '''sid INTEGER NOT NULL, uid INTEGER, name TEXT NOT NULL, 
        sort_order INTEGER, arc_ts INTEGER, PRIMARY KEY (name, sid)''', '(name, sid)'),
    _MT.SEIGA: ('oh_seiga_v1', '''sid INTEGER PRIMARY KEY NOT NULL, uid INTEGER, title TEXT, description TEXT, pages INTEGER, 
        is_doujin INTEGER DEFAULT 0, is_ai INTEGER DEFAULT 0, is_gore INTEGER DEFAULT 0, hall TEXT, 
        pub_ts INTEGER, arc_ts INTEGER, fav INTEGER, view INTEGER, comment_count INTEGER''', 'sid'),
    _MT.SEIGA_TAG: ('oh_seiga_tag_v1', 'tid INTEGER PRIMARY KEY NOT NULL, name TEXT NOT NULL', 'tid'),
    _MT.SEIGA_TAGMAP: ('oh_seiga_tagmap_v1', '''sid INTEGER NOT NULL, tid INTEGER NOT NULL, is_locked INTEGER DEFAULT 0, 
        lock_sort INTEGER DEFAULT 0, added_by INTEGER, arc_ts INTEGER, PRIMARY KEY (sid, tid)''', '(sid, tid)'),
    _MT.SEIGA_PAGE: ('oh_seiga_page_v1', '''sid INTEGER PRIMARY KEY NOT NULL, page_no INTEGER, asset_id INTEGER, original BLOB, 
        original_url TEXT, width INTEGER, height INTEGER, is_animated INTEGER DEFAULT 0, arc_ts INTEGER, CHECK 
        ((original IS NULL AND original_url IS NOT NULL) OR (original IS NOT NULL AND original_url IS NULL))''', 'sid'),
    _MT.VIDEO: ('oh_video_v1', '''vid INTEGER PRIMARY KEY NOT NULL, uid INTEGER, title TEXT, intro TEXT, vid_type INTEGER, 
        category INTEGER, channel_id INTEGER, tags TEXT, pub_ts INTEGER, like INTEGER, fav INTEGER, view INTEGER,
        comment INTEGER, cover_url TEXT, cover BLOB, video_url TEXT, video_local TEXT, video_m3u8_url TEXT,
        audio_url TEXT, dur INTEGER, arc_ts INTEGER, CHECK (((video_url IS NULL AND video_local IS NOT NULL) OR 
        (video_url IS NOT NULL AND video_local IS NULL)) AND ((cover IS NULL AND cover_url IS NOT NULL) OR 
        (cover IS NOT NULL AND cover_url IS NULL)))''', 'vid'),
    _MT.MEDIA: ('oh_media_v1', '''m_id INTEGER PRIMARY KEY NOT NULL, uid INTEGER, ext TEXT, title TEXT, description TEXT, 
        tags TEXT, orig_source TEXT, media_type TEXT, copyright_type INTEGER, file_size INTEGER, pub_ts INTEGER, 
        file_url TEXT, file_local TEXT, fav INTEGER, arc_ts INTEGER, CHECK((file_url IS NULL AND file_local IS NOT NULL) 
        OR (file_url IS NOT NULL AND file_local IS NULL))''', 'm_id'),
    _MT.CHANNEL: ('oh_channel_v1', '''cid INTEGER PRIMARY KEY NOT NULL, name TEXT, title TEXT, description TEXT, cover BLOB, 
        cover_url TEXT, creator_uid INTEGER, owner_uid INTEGER, admin_uid_list TEXT, join_permission INTEGER, 
        open_post INTEGER, member INTEGER, follower INTEGER, create_ts INTEGER, update_ts INTEGER, arc_ts INTEGER,
        CHECK ((cover_url IS NULL AND cover IS NOT NULL) OR (cover_url IS NOT NULL AND cover IS NULL))''', 'cid'),
    _MT.CHANNEL_SECTION: ('oh_channel_section_v1', '''cid INTEGER, section_id INTEGER, name TEXT, description TEXT, icon_url TEXT, 
        icon BLOB, sort_order INTEGER, creator_uid INTEGER, create_ts INTEGER, update_ts INTEGER, arc_ts INTEGER,
        is_deleted INTEGER, video INTEGER, blog INTEGER, total INTEGER, PRIMARY KEY (cid, section_id), CHECK (
        (icon_url IS NULL AND icon IS NOT NULL) OR (icon_url IS NOT NULL AND icon IS NULL))''', '(cid, section_id)'),
    _MT.CHANNEL_NOTICE: ('oh_channel_notice_v1', '''cid INTEGER, notice_id INTEGER, title TEXT, content TEXT, sort_order INTEGER,
        creator_uid INTEGER, create_ts INTEGER, update_ts INTEGER, arc_ts INTEGER, is_deleted INTEGER, 
        PRIMARY KEY (cid, notice_id)''', '(cid, notice_id)'),
}
##########################################################################################
# {api_k: str -> tuple[db_k: str, factory: callable]}
_MAP_USER = {'uid': ('uid', int), 'username': ('name', None), 'intro': ('intro', None),
             'time': ('create_ts', parseTime), 'sex': ('sex', None),
             'honour': ('honour', None), 'experience': ('exp', int), 'video_num': ('video', int),
             'blog_num': ('blog', int), 'seiga_num': ('seiga', int), 'media_num': ('media', int),
             'followings_count': ('follow', int), 'fans_count': ('fan', int)}
# _MAP_BLOG_API特殊处理forward_died。
_MAP_BLOG_API = {'bid': ('bid', int), 'uid': ('uid', int), 'time': ('pub_ts', parseTime), 'like_count': ('like', int),
                 'favorite_count': ('fav', int), 'view_count': ('view', int), 'attached_vid': ('attached_vid', int),
                 'copyright_type': ('copyright_type', int), 'blog_type': ('blog_type', int),
                 'comment_count': ('comment_count', int), 'title': ('title', None), 'content': ('content', None),
                 'is_gore': ('gore', int), 'tag': ('tags', _tag_factory), 'channel_id': ('channel', int),
                 'forward_bid': ('forward_bid', None)}
# _MAP_OBC_API特殊处理bid, API不返回。
_MAP_OBC_API = {'bcid': ('bcid', int), 'uid': ('uid', int), 'parent_bcid': ('parent_bcid', int),
                'time': ('pub_ts', parseTime), 'content': ('content', None), 'child_comment_num': ('reply_count', int),
                'pin_order': ('pin_order', int)}
_MAP_BLOG_ENTRY = {'bid': ('bid', int), 'uid': ('uid', int), 'timestamp': ('pub_ts', None), 'like_count': ('like', int),
                   'favorite_count': ('fav', int), 'view_count': ('view', int), 'attached_vid': ('attached_vid', int),
                   'copyright_type': ('copyright_type', int), 'blog_type': ('blog_type', int),
                   'title': ('title', None), 'content': ('content', None), 'tags': ('tags', _tag_factory),
                   'arc_time': ('arc_ts', None), 'channel_id': ('channel', None), 'is_gore': ('gore', int),
                   'forward_bid': ('forward_bid', None), 'is_unavailable': ('forward_died', int)}
# Comment类没有bid/vid/sid字段。
_MAP_OBC = {'cid': ('bcid', None), 'uid': ('uid', None), 'timestamp': ('pub_ts', None), 'content': ('content', None),
            'reply_count': ('reply_count', None), 'pin_order': ('pin_order', None), 'parent_cid': ('parent_bcid', None)}
_MAP_OVC = {'cid': ('vcid', None), 'uid': ('uid', None), 'timestamp': ('pub_ts', None), 'content': ('content', None),
            'reply_count': ('reply_count', None), 'pin_order': ('pin_order', None), 'parent_cid': ('parent_vcid', None)}
_MAP_OSC = {'cid': ('scid', None), 'uid': ('uid', None), 'timestamp': ('pub_ts', None), 'content': ('content', None),
            'reply_count': ('reply_count', None), 'pin_order': ('pin_order', None), 'parent_cid': ('parent_scid', None)}
# _MAP_OSC_API特殊处理sid, API不返回。
_MAP_OSC_API = {'bcid': ('scid', int), 'uid': ('uid', int), 'parent_scid': ('parent_scid', int),
                'time': ('pub_ts', parseTime), 'content': ('content', None), 'child_comment_num': ('reply_count', int)}
_MAP_SEIGA_API = {'sid': ('sid', int), 'uid': ('uid', int), 'title': ('title', None), 'view_count': ('view', int),
                  'description': ('description', None), 'page_count': ('pages', int), 'is_fanwork': ('is_doujin', int),
                  'hall_at': ('hall', None), 'is_ai': ('is_ai', int), 'is_gore': ('is_gore', int),
                  'time': ('pub_ts', parseTime), 'favorite_count': ('fav', int),
                  'comment_count': ('comment_count', int)}
# _MT.FOLLOW不需要map。
# _MAP_*_COLL_API特殊处理name, arc_ts。
_MAP_BLOG_COLL_API = {'bid': ('bid', int), 'uid': ('uid', int), 'collection_sort_order': ('sort_order', int)}
_MAP_VIDEO_COLL_API = {'vid': ('vid', int), 'uid': ('uid', int), 'collection_sort_order': ('sort_order', int)}
_MAP_SEIGA_COLL_API = {'sid': ('sid', int), 'uid': ('uid', int), 'collection_sort_order': ('sort_order', int)}
# _MT.SEIGA_PAGE, _MT.SEIGA_TAG, _MT.SEIGA_TAGMAP不需要map。
#########################################################################################
# map_type: int -> map: dict
# sql_type集合是map_type集合的真子集。
# 未做map：
# (17, 'oh_video_v1'),
# (18, 'oh_media_v1'), (19, 'oh_channel_v1'), (20, 'oh_channel_section_v1'), (21, 'oh_channel_notice_v1')]
# 各种2DB返回的是sql_type不是map_type。
# 我服了我自己了，写出来一个奇丑的tuple[tuple[int, dict], tuple[int, list[dict]], tuple[int, list[dict]], tuple[int, list[dict]]]。
# 最后还是改了。
# 我在干什么。现在(*2026/9/12)凌晨2点半了。果然熬夜写这个不好。
_META_MAP = {
    _MT.USER: _MAP_USER, _MT.BLOG: _MAP_BLOG_API, _MT.M_OBC_API: _MAP_OBC_API, _MT.M_BLOG_ENTRY: _MAP_BLOG_ENTRY,
    _MT.OBC: _MAP_OBC, _MT.OVC: _MAP_OVC, _MT.OSC: _MAP_OSC, _MT.M_OSC_API: _MAP_OSC_API,
    _MT.BLOG_COLL: _MAP_BLOG_COLL_API, _MT.VIDEO_COLL: _MAP_VIDEO_COLL_API, _MT.SEIGA_COLL: _MAP_SEIGA_COLL_API,
    _MT.SEIGA: _MAP_SEIGA_API,
}
#########################################################################################


def _process(data: dict, sql_type: _MT) -> dict:
    mapped = {}
    for api_key, (db_key, factory) in _META_MAP[sql_type].items():
        if api_key in data:
            if factory is None:
                mapped[db_key] = data[api_key]
            else:
                mapped[db_key] = factory(data[api_key])
    return mapped


@startEnd
def user2DB(data: dict, send_request: bool = True, config: Config = None) -> tuple[_SQLBatch]:
    """映射getUserDetail(...)的字段至oh_user，附处理。
    send_request: 是否发送请求以获取用户头像和封面，默认为True。"""
    if config is None:
        config = getGlobalConfig()
    mapped = _process(data, _MT.USER)  # 1
    mapped['arc_ts'] = int(time())  # 使用当前时间代替
    if send_request:
        mapped['avatar'] = _request('get', 'content', 'user2DB', data['avatar_url'], config=config)
        mapped['cover_h'] = _request('get', 'content', 'user2DB', data['cover_h_url'], config=config)
        mapped['cover_v'] = _request('get', 'content', 'user2DB', data['cover_v_url'], config=config)
    else:
        mapped['avatar_url'] = mapped['avatar_url']
        mapped['cover_h_url'], mapped['cover_v_url'] = data['cover_h_url'], data['cover_v_url']
    return _SQLBatch(_MT.USER, mapped),


def blog2DB(data: Union[dict, BlogEntry]) -> tuple[_SQLBatch]:
    """映射getBlogDetail(...)和BlogEntry的字段至oh_blog。"""
    if isinstance(data, BlogEntry):
        data = data.toDictShallow()
        mapped = _process(data, _MT.M_BLOG_ENTRY)  # 4
        mapped['comment_count'] = len(flattenComments(data['comments']))
    else:
        mapped = _process(data, _MT.BLOG)  # 2
        mapped['arc_ts'] = int(time())  # 使用当前时间代替
        mapped['forward_died'] = data['forward'].get('is_unavailable')
    return _SQLBatch(_MT.BLOG, mapped),


def commentRaw2DB(data: list[dict], from_id: int = 0) -> tuple[_SQLBatch]:
    """不建议使用。
    映射_get*CommentList(...)的字段至对应的数据表。会自动判断评论类型。
    提供from_id: int以向表中存储评论所在的bid/sid字段。"""
    res = []
    id_ = _MT.UNKNOWN
    if len(data) == 0:
        return _SQLBatch(id_, []),
    if data[0].get("bcid"):
        # blog
        for b in data:
            mapped = _process(b, _MT.M_OBC_API)  # 3
            if from_id:
                mapped['bid'] = from_id
            res.append(mapped)
        id_ = _MT.M_OBC_API
    elif data[0].get("scid"):
        # seiga
        for b in data:
            mapped = _process(b, _MT.M_OSC_API)  # 8
            if from_id:
                mapped['sid'] = from_id
            res.append(mapped)
        id_ = _MT.M_OSC_API
    return _SQLBatch(id_, res),


def comment2DB(data: Comment[Union[BlogEntry, VideoEntry]], from_id: int = 0) -> tuple[_SQLBatch]:
    """映射getAll*Comments(...)和Comment的字段至对应的数据表。
    提供from_id: int以向表中存储评论所在的bid/vid/sid字段。"""
    if data.c_type == 'blog':
        d = asdict(data)
        mapped = _process(d, _MT.OBC)  # 5
        if from_id:
            mapped['bid'] = from_id
        id_ = _MT.OBC
    elif data.c_type == 'video':
        d = asdict(data)
        mapped = _process(d, _MT.OVC)  # 6
        if from_id:
            mapped['vid'] = from_id
        id_ = _MT.OVC
    elif data.c_type == 'seiga':
        d = asdict(data)
        mapped = _process(d, _MT.OSC)  # 7
        if from_id:
            mapped['sid'] = from_id
        id_ = _MT.OSC
    else:
        raise ValueError(f'不支持的Comment.c_type类型: {data.c_type}')
    return _SQLBatch(id_, mapped),


def following2DB(data: list[dict], main_uid: int) -> tuple[_SQLBatch]:
    """映射关注的用户信息至数据表。需要提供main_uid (关注者uid)。
    data可以从ohutils.user_api.getAllFollowings(main_uid)获取。"""
    result = []
    for relation in data:
        result.append((main_uid, relation['uid']))
    return _SQLBatch(_MT.FOLLOW, result),


@startEnd
def seiga2DB(data: dict, send_request: bool = False, config: Config = None) -> tuple[_SQLBatch, _SQLBatch,
                                                                                     _SQLBatch, _SQLBatch]:
    """映射getSeigaDetail(...)的字段至数据表。
    send_request: 是否发送请求以获取原始静画，默认为False(仅存储URL)。"""
    sid = int(data['sid'])
    mapped = _process(data, _MT.SEIGA)  # 13
    tag_dicts, tagmap_dicts, page_dicts = [], [], []
    for t in data['tags']:
        tid = int(t['tag_id'])
        tag_dicts.append({'tid': tid, 'name': t['tag_name']})
        tagmap_dicts.append({'sid': sid, 'tid': tid, 'is_locked': t['is_locked'],
                             'lock_sort': t['lock_sort'], 'added_by': int(t['added_by_uid'])})
    for p in data['pages']:
        p_dict = {'sid': sid, 'page_no': int(p['page_no']), 'asset_id': int(p['image_asset_id']),
                  'width': int(p['width']), 'height': int(p['height']), 'is_animated': p['is_animated']}
        if send_request:
            p_dict['original'] = _request('get', 'content', 'seiga2DB', data['original_url'], config=config)
        else:
            p_dict['original_url'] = p['original_url']
        page_dicts.append(p_dict)
    return (_SQLBatch(_MT.SEIGA, mapped), _SQLBatch(_MT.SEIGA_TAG, tag_dicts),
            _SQLBatch(_MT.SEIGA_TAGMAP, tagmap_dicts), _SQLBatch(_MT.SEIGA_PAGE, page_dicts))


def collection2DB(data: dict) -> tuple[_SQLBatch]:
    res = []
    if 'blog_list' in data:
        for b in data['blog_list']:
            mapped = _process(b, _MT.BLOG_COLL)
            mapped['arc_ts'] = int(time())  # 使用当前时间代替
            mapped['name'] = data['collection']
            res.append(mapped)
        id_ = _MT.BLOG_COLL
    elif 'video_list' in data:
        for b in data['video_list']:
            mapped = _process(b, _MT.VIDEO_COLL)
            mapped['arc_ts'] = int(time())
            mapped['name'] = data['collection']
            res.append(mapped)
        id_ = _MT.VIDEO_COLL
    elif 'seiga_list' in data:
        for b in data['seiga_list']:
            mapped = _process(b, _MT.SEIGA_COLL)
            mapped['arc_ts'] = int(time())
            mapped['name'] = data['collection']
            res.append(mapped)
        id_ = _MT.SEIGA_COLL
    else:
        raise ValueError(f'不支持的collection类型')
    return _SQLBatch(id_, res),



def auto2DB(data, **kwargs):
    """自动判断类型并映射字段。
    main_uid: (仅following)关注者uid。
    from_id: (可选，仅Comment)评论所在的bid/vid/sid字段。
    send_request: (可选，仅user dict和seiga dict)是否发送请求以获取用户头像和封面，默认为True。
    config: (可选，仅user dict和seiga dict)配置。"""
    if isinstance(data, BlogEntry):
        return blog2DB(data)  # blog2DB的BlogEntry式
    if isinstance(data, Comment):
        return comment2DB(data, **kwargs)
    if isinstance(data, list):
        if not data:
            return (0, []),
        if 'bcid' in data[0] or 'scid' in data[0]:
            return commentRaw2DB(data, **kwargs)
        if 'follow_status' in data[0]:
            return following2DB(data, **kwargs)
    if isinstance(data, dict):
        if 'bid' in data and 'title' in data:
            return blog2DB(data)  # blog2DB的dict式
        if 'uid' in data and 'experience' in data and 'sex' in data:
            return user2DB(data, **kwargs)
        if 'sid' in data and 'description' in data:
            return seiga2DB(data, **kwargs)
        if 'collection' in data:
            return collection2DB(data)
    raise ValueError("无法识别数据类型")


def loadTable(sql_type: int, config: Config = None) -> sqlite3.Connection:
    """记得conn.close()"""
    if config is None:
        config = getGlobalConfig()
    conn = sqlite3.connect(os.path.join(config.indexPath, config.SQLName))
    cur = conn.cursor()
    table_name, table_def, _ = _MAP[sql_type]
    cur.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({table_def})')
    return conn


def _writeData(sql_type: _MT, data: dict, conn: sqlite3.Connection, no_update: bool = False):
    cur = conn.cursor()
    keys = data.keys()
    table_name, _, prim_key = _MAP[sql_type]
    if no_update:
        cur.execute(
            f"INSERT OR IGNORE INTO {table_name} ({', '.join(keys)}) VALUES ({', '.join('?' * len(keys))})",
            tuple(data.values())
        )
    else:
        conflict = f"ON CONFLICT({prim_key}) DO UPDATE SET " + \
                   ", ".join([f"{k} = excluded.{k}" for k in keys if k != prim_key])
        cur.execute(
            f"INSERT INTO {table_name} ({', '.join(keys)}) VALUES ({', '.join('?' * len(keys))}) {conflict}",
            tuple(data.values())
        )
    conn.commit()


def writeSQL(batches: tuple[_SQLBatch], no_update: bool = False, config: Config = None):
    """批量写入数据库。接收来自*2DB的值。"""
    if config is None:
        config = getGlobalConfig()
    conn = sqlite3.connect(os.path.join(config.indexPath, config.SQLName))
    cur = conn.cursor()
    for sql_ in batches:
        sql_type, sql_dict = sql_.sql_type, sql_.data
        if sql_type == 0:
            continue
        table_name, table_def, _ = _MAP[sql_type]
        cur.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({table_def})')
        _writeData(sql_type, sql_dict, conn, no_update)
    conn.close()


def readData(sql_type: int, conn: sqlite3.Connection, fields: list = None, **kwargs) -> list:
    """从指定数据库读取选择的字段(fields)，带条件。
    条件的比较运算符: 若无后缀，为等于(=)。
    若有__gt / __lt / __ge / __le / __ne / __like后缀，
    则分别为大于(>)，小于(<)，大于等于(>=)，小于等于(<=)，不等于(!=)，LIKE。

    e.g.:
    view__le=132 -> view <= 132
    exp__gt=100 -> exp > 100
    fav=15 -> fav = 15
    """
    cur = conn.cursor()
    fields_str = ", ".join(fields) if fields else "*"
    kv = []
    map_ = {'lt': '<', 'gt': '>', 'le': '<=', 'ge': '>=', 'ne': '!=', 'like': ' LIKE '}
    for k in kwargs.keys():
        # 哦还有rsplit这种东西的啊。
        k_list = k.rsplit('__', maxsplit=1)
        if len(k_list) == 1:
            kv.append(k + '=?')  # 无后缀
        else:
            if k_list[1] not in map_.keys():
                map_[k_list[1]] = '__' + k_list[1]  # 若误分割，拼回来
            kv.append(k_list[0] + map_[k_list[1]] + '?')
    cond = ('WHERE ' if kwargs.keys() else '') + " AND ".join(kv)
    query = f"SELECT {fields_str} FROM {_MAP[sql_type][0]} {cond}"
    cur.execute(query, tuple(kwargs.values()))
    return cur.fetchall()


def init(config: Config = None):
    """初始化数据库，创建所有表。"""
    if config is None:
        config = getGlobalConfig()
    conn = sqlite3.connect(os.path.join(config.indexPath, config.SQLName))
    cur = conn.cursor()
    tables = _MAP.values()
    for t in tables:
        table_name, table_def, _ = t
        cur.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({table_def})')
    conn.close()
