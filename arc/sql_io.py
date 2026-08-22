import sqlite3
import os
from typing import Union
from time import time
from ..core.config import Config, getGlobalConfig
from ..core.util import parseTime, _request, startEnd, BlogEntry, flattenComments, Comment, VideoEntry
from dataclasses import asdict

# {sql_type: int -> tuple[table_name: str, table_def: str, prim_key: str]}
_MAP = {1: ('oh_user_v1', '''uid INTEGER PRIMARY KEY NOT NULL, name TEXT, intro TEXT, create_ts INTEGER,
        sex TEXT, honour TEXT, exp INTEGER, avatar BLOB, cover_h BLOB, cover_v BLOB, video INTEGER, blog INTEGER,
        seiga INTEGER, media INTEGER, follow INTEGER, fan INTEGER''', 'uid'),
        2: ('oh_blog_v1', '''bid INTEGER PRIMARY KEY NOT NULL, uid INTEGER, pub_ts INTEGER, arc_ts INTEGER,
        channel INTEGER, like INTEGER, fav INTEGER, view INTEGER, attached_vid INTEGER, copyright_type INTEGER,
        blog_type INTEGER, comment_count INTEGER, title TEXT, content TEXT, tags TEXT, gore INTEGER''', 'bid'),
        3: ('oh_obc_v1', '''bcid INTEGER PRIMARY KEY NOT NULL, bid INTEGER, uid INTEGER, parent_bcid INTEGER DEFAULT 0,
        pub_ts INTEGER, content TEXT, reply_count INTEGER DEFAULT 0, pin_order INTEGER DEFAULT 0''', 'bcid'),
        6: ('oh_ovc_v1', '''vcid INTEGER PRIMARY KEY NOT NULL, vid INTEGER, uid INTEGER, parent_vcid INTEGER DEFAULT 0,
        pub_ts INTEGER, content TEXT, reply_count INTEGER DEFAULT 0, pin_order INTEGER DEFAULT 0''', 'vcid'),
        7: ('oh_osc_v1', '''scid INTEGER PRIMARY KEY NOT NULL, sid INTEGER, uid INTEGER, parent_scid INTEGER DEFAULT 0, 
        pub_ts INTEGER, content TEXT, reply_count INTEGER DEFAULT 0, pin_order INTEGER DEFAULT 0''', 'scid'),
        9: ('oh_follow_v1', 'uid INTEGER, target_uid INTEGER, PRIMARY KEY (uid, target_uid)', '(uid, target_uid)')}
##########################################################################################
# {api_k: str -> tuple[db_k: str, factory: callable]}
_MAP_USER = {'uid': ('uid', int), 'username': ('name', None), 'intro': ('intro', None),
             'time': ('create_ts', parseTime), 'sex': ('sex', None),
             'honour': ('honour', None), 'experience': ('exp', int), 'video_num': ('video', int),
             'blog_num': ('blog', int), 'seiga_num': ('seiga', int), 'media_num': ('media', int),
             'followings_count': ('follow', int), 'fans_count': ('fan', int)}
_MAP_BLOG = {'bid': ('bid', int), 'uid': ('uid', int), 'time': ('pub_ts', parseTime), 'like_count': ('like', int),
             'favorite_count': ('fav', int), 'view_count': ('view', int), 'attached_vid': ('attached_vid', int),
             'copyright_type': ('copyright_type', int), 'blog_type': ('blog_type', int),
             'comment_count': ('comment_count', int), 'title': ('title', None), 'content': ('content', None),
             'is_gore': ('gore', int), 'tag': ('tags', lambda x: ','.join(x)), 'channel_id': ('channel', int)}
# _MAP_OBC_API特殊处理bid, API不返回。
_MAP_OBC_API = {'bcid': ('bcid', int), 'uid': ('uid', int), 'parent_bcid': ('parent_bcid', int),
                'time': ('pub_ts', parseTime), 'content': ('content', None), 'child_comment_num': ('reply_count', int),
                'pin_order': ('pin_order', int)}
_MAP_BLOG_ENTRY = {'bid': ('bid', int), 'uid': ('uid', int), 'timestamp': ('pub_ts', None), 'like_count': ('like', int),
                   'favorite_count': ('fav', int), 'view_count': ('view', int), 'attached_vid': ('attached_vid', int),
                   'copyright_type': ('copyright_type', int), 'blog_type': ('blog_type', int),
                   'title': ('title', None), 'content': ('content', None), 'tags': ('tags', lambda x: ','.join(x)),
                   'arc_time': ('arc_ts', None), 'channel_id': ('channel', None), 'is_gore': ('gore', int)}
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
_MAP_FOLLOW = {}
#########################################################################################
_META_MAP = {1: _MAP_USER, 2: _MAP_BLOG, 3: _MAP_OBC_API, 4: _MAP_BLOG_ENTRY, 5: _MAP_OBC, 6: _MAP_OVC, 7: _MAP_OSC,
             8: _MAP_OSC_API, 9: _MAP_FOLLOW}
#########################################################################################


def _process(data: dict, sql_type: int):
    mapped = {}
    for api_key, (db_key, factory) in _META_MAP[sql_type].items():
        if api_key in data:
            if factory is None:
                mapped[db_key] = data[api_key]
            else:
                mapped[db_key] = factory(data[api_key])
    return mapped


@startEnd
def user2DB(data: dict, send_request: bool = True, config: Config = None) -> dict:
    """映射getUserDetailRaw(...)的字段至oh_user，附处理。
    send_request: 是否发送请求以获取用户头像和封面，默认为True。"""
    if config is None:
        config = getGlobalConfig()
    mapped = _process(data, 1)  # 1: USER
    if send_request:
        mapped['avatar'] = _request('get', 'content', 'user2DB', data['avatar_url'], config=config)
        mapped['cover_h'] = _request('get', 'content', 'user2DB', data['cover_h_url'], config=config)
        mapped['cover_v'] = _request('get', 'content', 'user2DB', data['cover_v_url'], config=config)
    return mapped


def blog2DB(data: Union[dict, BlogEntry]) -> dict:
    """映射getBlogRaw(...)和BlogEntry的字段至oh_blog。"""
    if isinstance(data, BlogEntry):
        data = data.toDictShallow()
        mapped = _process(data, 4)  # 4: BLOG_ENTRY
        mapped['comment_count'] = len(flattenComments(data['comments']))
    else:
        mapped = _process(data, 2)  # 2: BLOG
        mapped['arc_ts'] = int(time())  # 使用当前时间代替
    return mapped


def commentRaw2DB(data: list[dict], from_id: int = 0) -> list[dict]:
    """映射get*CommentListRaw(...)的字段至对应的数据表。会自动判断评论类型。
    提供from_id: int以向表中存储评论所在的bid/sid字段。"""
    res = []
    if data.get("bcid"):
        # blog
        for b in data:
            mapped = _process(b, 3)  # 3: OBC_API
            if from_id:
                mapped['bid'] = from_id
            res.append(mapped)
    elif data.get("scid"):
        # seiga
        for b in data:
            mapped = _process(b, 8)  # 8: OSC_API
            if from_id:
                mapped['sid'] = from_id
            res.append(mapped)
    return res


def comment2DB(data: Comment[Union[BlogEntry, VideoEntry]], from_id: int = 0):
    """映射getAll*Comments(...)和Comment的字段至对应的数据表。
    提供from_id: int以向表中存储评论所在的bid/vid/sid字段。"""
    if data.c_type == 'blog':
        d = asdict(data)
        mapped = _process(d, 5)  # 5: OBC
        if from_id:
            mapped['bid'] = from_id
    elif data.c_type == 'video':
        d = asdict(data)
        mapped = _process(d, 6)  # 6: OVC
        if from_id:
            mapped['vid'] = from_id
    elif data.c_type == 'seiga':
        d = asdict(data)
        mapped = _process(d, 7)  # 7: OSC
        if from_id:
            mapped['sid'] = from_id
    else:
        raise ValueError(f'不支持的Comment.c_type类型: {data.c_type}')
    return mapped


def loadTable(sql_type: int, config: Config = None) -> sqlite3.Connection:
    """记得conn.close()"""
    if config is None:
        config = getGlobalConfig()
    conn = sqlite3.connect(os.path.join(config.indexPath, config.SQLName))
    cur = conn.cursor()
    table_name, table_def, _ = _MAP[sql_type]
    cur.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({table_def})')
    return conn


def writeData(sql_type: int, conn: sqlite3.Connection, no_update: bool = False, **kw):
    cur = conn.cursor()
    keys = kw.keys()
    table_name, _, prim_key = _MAP[sql_type]
    if no_update:
        cur.execute(
            f"INSERT OR IGNORE INTO {table_name} ({', '.join(keys)}) VALUES ({', '.join('?' * len(keys))})",
            tuple(kw.values())
        )
    else:
        conflict = f"ON CONFLICT({prim_key}) DO UPDATE SET " + \
                   ", ".join([f"{k} = excluded.{k}" for k in keys if k != prim_key])
        cur.execute(
            f"INSERT INTO {table_name} ({', '.join(keys)}) VALUES ({', '.join('?' * len(keys))}) {conflict}",
            tuple(kw.values())
        )
    conn.commit()


def readData(sql_type: int, conn: sqlite3.Connection, fields: list = None, **kwargs) -> list:
    cur = conn.cursor()
    fields_str = ", ".join(fields) if fields else "*"
    cond = 'WHERE ' if kwargs.keys() else '' + " AND ".join([f"{k} = ?" for k in kwargs.keys()])
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
