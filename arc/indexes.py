import glob
import re
import os
import json
from ..core.util import getVersion, flattenComments
from .obarc import loadObarcMerged
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
    for path in glob.glob(os.path.join(config.savePath, config.regexName)):
        bid = int(re.search(r'ob(\d+)', path).group(1))
        try:
            blog = loadObarcMerged(bid, config)
            index[bid] = {
                'bid': bid,
                'uid': blog.uid,
                'ts': blog.timestamp,
                'arcts': blog.arc_time,
                'c_len': len(blog.comments),  # comment_count
                'ver': getVersion(path),
                'size': os.path.getsize(path),
                'title': blog.title,
            }
        except Exception as e:
            index[bid] = {'error': str(e)}
    with open(os.path.join(config.indexPath, config.indexName), "w") as f:
        json.dump(index, f)
    return True


def buildUserCommentIdx(config: Config = None):
    if config is None:
        config = getGlobalConfig()
    index = {}
    for path in glob.glob(os.path.join(config.savePath, config.regexName)):
        bid = int(re.search(r'ob(\d+)', path).group(1))
        try:
            blog = loadObarcMerged(bid, config)
            for c in flattenComments(blog.comments):
                uid = c.uid
                index[uid] = index.get(uid, [])
                index[uid].append({
                    'bcid': c.bcid,
                    'bid': bid,
                    'timestamp': c.timestamp,
                    'content': c.content,
                    'reply_count': c.reply_count
                })
        except Exception as e:
            if config.verbose:
                print(f"[buildUserCommentIdx]Skip: {e}")
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
    for path in glob.glob(os.path.join(config.savePath, config.regexName)):
        bid = int(re.search(r'ob(\d+)', path).group(1))
        try:
            blog = loadObarcMerged(bid, config)
            for c in flattenComments(blog.comments):
                bcid = c.bcid
                index[bcid] = {
                    'uid': c.uid,
                    'bid': bid,
                    'timestamp': c.timestamp,
                    'content': c.content,
                    'reply_count': c.reply_count,
                }
        except Exception as e:
            if config.verbose:
                print(f"[buildOBCCommentIdx]Skip: {e}")
    with open(os.path.join(config.indexPath, config.OBCCommentIdxName), "w") as f:
        json.dump(index, f)
    return True


def loadOBCCommentIdx(config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    with open(os.path.join(config.indexPath, config.OBCCommentIdxName), "r") as fp:
        return json.load(fp)
