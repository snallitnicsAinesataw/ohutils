from .util import startEnd, Comment, parseTime, _request, APIError
from .exceptions import ExhaustedRetriesError
from .config import Config, getGlobalConfig
import requests
import time
from typing import List
from random import random


@startEnd
def getBlogRaw(bid: int, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/blog/{bid}/detail/"
    return _request('get', 'json', 'getBlogRaw', url, config)


@startEnd
def getLatestBlogRaw(offset: int = 0, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/blog/latest?offset={offset}&num={config.latestBlogPerReq}"
    return _request('get', 'json', 'getLatestBlogRaw', url, config)


@startEnd
def getCommentListRaw(bid, parent_bcid=0, offset=0, config: Config = None) -> dict:
    """拉取一层评论（不递归）"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/comment/blogs/{bid}?parent_bcid={parent_bcid}&offset={offset}&num={config.commentPerReq}"
    return _request('get', 'json', 'getCommentListRaw', url, config)


@startEnd
def getAllComments(bid: int, parent_bcid: int = 0, config: Config = None) -> List[Comment]:
    """递归拉取所有评论"""
    if config is None:
        config = getGlobalConfig()
    all_comments = []
    offset = 0
    while True:
        if offset != 0 and config.verbose:
            print(f"[getAllComments]curr offset: {offset}")

        try:
            data = getCommentListRaw(bid, parent_bcid, offset, config)
        except ExhaustedRetriesError as e:
            if config.verbose:
                print(f"[getAllComments]{config.colorRed}fail to get all comments: {e}")
            return []  # 过于激进?

        comment_list = data['data'].get("comment_list", [])
        if not comment_list:
            return []  # 过于激进?

        for c in comment_list:
            child_num = int(c.get("child_comment_num", 0))
            comment = Comment(
                bcid=int(c["bcid"]),
                uid=int(c["uid"]),
                timestamp=parseTime(c['time']),
                content=c["content"],
                reply_count=c["child_comment_num"],
                replies=[]
            )

            if child_num > 0:
                if config.verbose:
                    print(f"[getAllComments]Get replies of bcid{comment.bcid}...")
                comment.replies = getAllComments(bid, comment.bcid, config)

            all_comments.append(comment)

        if len(comment_list) < config.commentPerReq:
            break
        offset += config.commentPerReq
        time.sleep(random() * 2)
    return all_comments


@startEnd
def sendComment(bid: int, content: str, parent_bcid: int = 0, config: Config = None):
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/comment/blogs/{bid}"
    data = {"token": config.token, "parent_bcid": str(parent_bcid), "content": content}
    return _request('post', 'json', "sendComment", url, config, data)


@startEnd
def getRandomBlogRaw(config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/blog/latest?num={config.randomBlogPerReq}"
    return _request('get', 'json', 'getRandomBlogRaw', url, config)


@startEnd
def searchBlogsRaw(term: str, offset: int = 0, bid_desc: bool = True, view_desc: bool = False,
                   config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/blog/search?search_term={term}&offset={offset}&num={config.searchBlogPerReq}" \
          f"&bid_desc={1 if bid_desc else 0}&view_count_desc={1 if view_desc else 0}"
    return _request('get', 'json', 'searchBlogsRaw', url, config)


@startEnd
def toggleBlogLike(bid: int, config: Config = None):
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/blog/like/{bid}"
    return _request('post', 'json', 'toggleBlogLike', url, config, {'token': config.token})


@startEnd
def toggleBlogFavorite(bid: int, config: Config = None):
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/blog/favorite/{bid}"
    return _request('post', 'json', 'toggleBlogFavorite', url, config, {'token': config.token})


@startEnd
def getManageBlogsRaw(offset: int = 0, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = (
        f"https://api.ottohub.cn/api/blog/manage-list?num={config.managePerReq}&offset={offset}&_t={int(time.time())}"
        f"&token={config.token}")
    return _request('get', 'json', "getManageBlogsRaw", url, config)


@startEnd
def getFavoriteBlogsRaw(offset: int = 0, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/blog/favorite-list?num={config.managePerReq}&offset={offset}" \
          f"&_t={int(time.time())}&token={config.token}"
    return _request('get', 'json', "getFavoriteBlogsRaw", url, config)


@startEnd
def editBlog(bid: int, tags: list[str] = None, is_gore: bool = None, config: Config = None):
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/blog/{bid}"
    data = {'token': config.token}
    if is_gore is not None:
        data['is_gore'] = int(is_gore)
    if tags is not None:
        data['tag'] = tags
    return _request('put', 'json', 'editBlog', url, config, data)