from .util import startEnd, Comment, parseTime, _requestJson, APIError, _postJson
from .exceptions import OttoBaseException
from .config import Config, getGlobalConfig
import requests
import time
from typing import List
from random import random


@startEnd
def getBlogRaw(bid: int, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    if config.alwaysUseToken:
        url = f"https://api.ottohub.cn/api/blog/{bid}/detail?token={config.token}"
    else:
        url = f"https://api.ottohub.cn/api/blog/{bid}/detail/"
    return _requestJson('getBlogRaw', url, config)


@startEnd
def getLatestBlogRaw(offset:int =0, config: Config = None) -> list:
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/blog/latest?offset={offset}&num={config.latestBlogPerReq}"
    return _requestJson('getLatestBlogRaw', url, config).get("blog_list", [])


@startEnd
def getCommentListRaw(bid, parent_bcid=0, offset=0, config: Config = None) -> dict:
    """拉取一层评论（不递归）"""
    if config is None:
        config = getGlobalConfig()
    if config.alwaysUseToken:
        url = f"https://api.ottohub.cn/api/comment/blogs/{bid}?parent_bcid={parent_bcid}"\
              f"&offset={offset}&num={config.commentPerReq}&token={config.token}"
    else:
        url = f"https://api.ottohub.cn/api/comment/blogs/{bid}?parent_bcid={parent_bcid}&offset={offset}&num={config.commentPerReq}"
    return _requestJson('getCommentListRaw', url, config)


@startEnd
def getAllComments(bid: int, parent_bcid: int = 0, config: Config = None) -> List[Comment]:
    """递归拉取所有评论"""
    if config is None:
        config = getGlobalConfig()
    all_comments = []
    offset = 0
    try:
        while True:
            if offset != 0 and config.verbose:
                print(f"[getAllComments]curr offset: {offset}")

            data = {'data': {}}   # dummy, TODO: edit this
            try:
                data = getCommentListRaw(bid, parent_bcid, offset, config)
            except Exception as e:
                print(e)
                p = input("[debug/getAllComments]break?")
                if p:
                    break

            comment_list = data['data'].get("comment_list", [])
            if not comment_list:
                break

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
    except (TimeoutError, ConnectionError) as e:
        if config.verbose:
            print(f"[getAllComments]{_RED}Network error: {e}")
        raise requests.RequestException(e)
    return all_comments


@startEnd
def sendComment(bid: int, content: str, parent_bcid: int = 0, config: Config = None):
    if config is None:
        config = getGlobalConfig()
    url = f"https://api.ottohub.cn/api/comment/blogs/{bid}"
    data = {"token": config.token, "parent_bcid": str(parent_bcid), "content": content}
    return _postJson("sendComment", url, data, config)
