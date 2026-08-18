import sqlite3
import os
from typing import Union
from time import time
from ..core.config import Config, getGlobalConfig
from ..core.util import parseTime, _request, startEnd, BlogEntry, flattenComments

# {sql_type: int -> tuple[table_name: str, table_def: str, prim_key: str]}
_MAP = {1: ('oh_user', '''uid INTEGER PRIMARY KEY NOT NULL, name TEXT, intro TEXT, create_ts INTEGER,
        sex TEXT, honour TEXT, exp INTEGER, avatar BLOB, cover BLOB, video INTEGER, blog INTEGER,
        seiga INTEGER, media INTEGER, follow INTEGER, fan INTEGER''', 'uid'),
        2: ('oh_blog', '''bid INTEGER PRIMARY KEY NOT NULL, uid INTEGER, pub_ts INTEGER, arc_ts INTEGER,
        channel INTEGER, like INTEGER, fav INTEGER, view INTEGER, attached_vid INTEGER, copyright_type INTEGER,
        blog_type INTEGER, comment_count INTEGER, title TEXT, content TEXT, tags TEXT, gore INTEGER''', 'bid'),
        3: ('oh_obc', '''bcid INTEGER PRIMARY KEY NOT NULL, bid INTEGER, uid INTEGER, parent_bcid INTEGER DEFAULT 0,
        timestamp INTEGER, content TEXT, reply_count INTEGER DEFAULT 0''', 'bcid'),
        6: ()}

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
_MAP_COMMENT_API = {}
_MAP_BLOG_ENTRY = {'bid': ('bid', int), 'uid': ('uid', int), 'timestamp': ('pub_ts', None), 'like_count': ('like', int),
                   'favorite_count': ('fav', int), 'view_count': ('view', int), 'attached_vid': ('attached_vid', int),
                   'copyright_type': ('copyright_type', int), 'blog_type': ('blog_type', int),
                   'title': ('title', None), 'content': ('content', None), 'tags': ('tags', lambda x: ','.join(x)),
                   'arc_time': ('arc_ts', None), 'channel_id': ('channel', None), 'is_gore': ('gore', int)}
_MAP_COMMENT = {}
_META_MAP = {1: _MAP_USER, 2: _MAP_BLOG, 3: _MAP_COMMENT, 4: _MAP_BLOG_ENTRY, 5: _MAP_COMMENT}


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
def User2DB(data: dict, send_request: bool = True, config: Config = None) -> dict:
    """映射getUserDetailRaw(...)的字段至oh_user，附处理"""
    if config is None:
        config = getGlobalConfig()
    mapped = _process(data, 1)
    if send_request:
        mapped['avatar'] = _request('get', 'content', 'User2DB', data['avatar_url'], config=config)
        mapped['cover'] = _request('get', 'content', 'User2DB', data['cover_url'], config=config)
    return mapped


def Blog2DB(data: Union[dict, BlogEntry]) -> dict:
    """映射getBlogRaw(...)和BlogEntry的字段至oh_blog"""
    if isinstance(data, BlogEntry):
        data = data.toDictShallow()
        mapped = _process(data, 4)  # 4: BLOG_ENTRY
        mapped['comment_count'] = len(flattenComments(data['comments']))
    else:
        mapped = _process(data, 2)  # 2: BLOG
        mapped['arc_ts'] = int(time())  # 使用当前时间代替
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
                   ", ".join([f"{k} = excluded.{k}" for k in keys if k != "uid"])
        cur.execute(
            f"INSERT INTO {table_name} ({', '.join(keys)}) VALUES ({', '.join('?' * len(keys))}) {conflict}",
            tuple(kw.values())
        )
    conn.commit()


def readData(sql_type: int, conn: sqlite3.Connection, fields: list = None, **kw):
    cur = conn.cursor()
    fields_str = ", ".join(fields) if fields else "*"
    cond = 'WHERE ' if kw.keys() else '' + " AND ".join([f"{k} = ?" for k in kw.keys()])
    query = f"SELECT {fields_str} FROM {_MAP[sql_type][0]} {cond}"
    cur.execute(query, tuple(kw.values()))
    return cur.fetchall()
