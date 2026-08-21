import glob
import re
import os
import json
from ..core.util import getVersion, flattenComments
from .obarc import loadObarc
from ..core.config import Config, getGlobalConfig


def loadBlogIndex(config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    with open(os.path.join(config.indexPath, config.indexName), "r") as fp:
        return json.load(fp)


def buildBlogIndex(config: Config = None):
    if config is None:
        config = getGlobalConfig()
    index = {}
    for path in glob.glob(os.path.join(config.savePath, config.blobName)):
        bid = int(re.search(r'ob(\d+)', path).group(1))
        try:
            blog = loadObarc(bid, config)
            index[bid] = {
                'bid': bid,
                'uid': blog.uid,
                'ts': blog.timestamp,
                'arcts': blog.arc_time,
                'c_len': len(flattenComments(blog.comments)),  # comment_count
                'ver': getVersion(path),
                'size': os.path.getsize(path),
                'title': blog.title,
                'fav': blog.favorite_count,
                'like': blog.like_count,
                'view': blog.view_count
            }
        except Exception as e:
            if config.verbose:
                print(f"[buildUserCommentIdx]Skip ob{bid}: {e}")
    with open(os.path.join(config.indexPath, config.indexName), "w") as f:
        json.dump(index, f)
    return True


def buildUserCommentIdx(config: Config = None):
    if config is None:
        config = getGlobalConfig()
    index = {}
    for path in glob.glob(os.path.join(config.savePath, config.blobName)):
        bid = int(re.search(r'ob(\d+)', path).group(1))
        try:
            blog = loadObarc(bid, config)
            for c in flattenComments(blog.comments):
                uid = c.uid
                index[uid] = index.get(uid, [])
                index[uid].append({
                    'bcid': c.cid,
                    'bid': bid,
                    'timestamp': c.timestamp,
                    'content': c.content,
                    'reply_count': c.reply_count
                })
        except Exception as e:
            if config.verbose:
                print(f"[buildUserCommentIdx]Skip ob{bid}: {e}")
    with open(os.path.join(config.indexPath, config.userCommentIdxName), "w") as f:
        json.dump(index, f)
    return True


def loadUserCommentIdx(config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    with open(os.path.join(config.indexPath, config.userCommentIdxName), "r") as fp:
        return json.load(fp)


def buildOBCCommentIdx(config: Config = None):
    if config is None:
        config = getGlobalConfig()
    index = {}
    for path in glob.glob(os.path.join(config.savePath, config.blobName)):
        bid = int(re.search(r'ob(\d+)', path).group(1))
        try:
            blog = loadObarc(bid, config)
            for c in flattenComments(blog.comments):
                bcid = c.cid
                index[bcid] = {
                    'uid': c.uid,
                    'bid': bid,
                    'timestamp': c.timestamp,
                    'content': c.content,
                    'reply_count': c.reply_count,
                }
        except Exception as e:
            if config.verbose:
                print(f"[buildOBCCommentIdx]Skip ob{bid}: {e}")
    with open(os.path.join(config.indexPath, config.OBCCommentIdxName), "w") as f:
        json.dump(index, f)
    return True


def loadOBCCommentIdx(config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    with open(os.path.join(config.indexPath, config.OBCCommentIdxName), "r") as fp:
        return json.load(fp)


def buildAllIndexes(config: Config = None):
    if config is None:
        config = getGlobalConfig()
    ob, c_obc, c_ou = {}, {}, {}
    for path in glob.glob(os.path.join(config.savePath, config.blobName)):
        bid = int(re.search(r'ob(\d+)', path).group(1))
        try:
            blog = loadObarc(bid, config)
            # ob部分
            ob[bid] = {'bid': bid, 'uid': blog.uid, 'ts': blog.timestamp, 'arcts': blog.arc_time,
                       'c_len': len(blog.comments), 'ver': getVersion(path), 'size': os.path.getsize(path),
                       'title': blog.title}
            # c_obc & c_ou部分
            for c in flattenComments(blog.comments):
                uid, bcid = c.uid, c.cid
                c_ou[uid] = c_ou.get(uid, [])
                c_obc[bcid] = {'uid': c.uid, 'bid': bid, 'timestamp': c.timestamp, 'content': c.content,
                               'reply_count': c.reply_count}
                c_ou[uid].append({'bcid': c.cid, 'bid': bid, 'timestamp': c.timestamp, 'content': c.content,
                                  'reply_count': c.reply_count})
        except Exception as e:
            if config.verbose:
                print(f"[buildAllIndexes]Skip ob{bid}: {e}")
    with open(os.path.join(config.indexPath, config.indexName), "w") as f:
        json.dump(ob, f)
    with open(os.path.join(config.indexPath, config.userCommentIdxName), "w") as f:
        json.dump(c_ou, f)
    with open(os.path.join(config.indexPath, config.OBCCommentIdxName), "w") as f:
        json.dump(c_obc, f)
    return True
