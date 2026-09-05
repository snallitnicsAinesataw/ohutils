from .util import startEnd, Comment, parseTime, _request, APIError, _recur_request
from .exception import ExhaustedRetriesError
from .config import Config, getGlobalConfig
import requests
import time
from typing import List, Union
import random


@startEnd
def getBlogDetail(bid: int, config: Config = None) -> dict:
    """获取指定bid的动态数据。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/blog/{bid}/detail/"
    res = _request('get', 'json', 'getBlogDetail', url, config=config)
    del res['status']
    return res


@startEnd
def getLatestBlog(offset: int = 0, config: Config = None) -> list[dict]:
    """获取最近的动态。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/blog/latest?offset={offset}&num={config.latestBlogPerReq}" +\
          ('' if config.gore else f"&is_gore=0")
    return _request('get', 'json', 'getLatestBlog', url, config=config)['blog_list']


@startEnd
def _getBlogCommentList(bid, parent_bcid: int = 0, offset: int = 0,
                        cid_asc: bool = True, include_pinned: bool = True, config: Config = None) -> dict:
    """拉取指定bid的一组评论(不递归)。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/comment/blogs/{bid}?parent_bcid={parent_bcid}&offset={offset}"\
          f"&num={config.commentPerReq}&cid_asc={int(cid_asc)}&include_pinned={int(include_pinned)}"
    return _request('get', 'json', '_getBlogCommentList', url, config=config)['data']['comment_list']


@startEnd
def getAllBlogComments(bid: int, parent_bcid: int = 0,
                       include_pinned: bool = True, config: Config = None) -> list[Comment]:
    """递归拉取指定bid的所有评论。"""
    if config is None:
        config = getGlobalConfig()
    all_comments, offset = [], 0
    while True:
        if offset != 0 and config.verbose:
            print(f"[getAllBlogComments]curr offset: {offset}")

        try:
            comment_list = _getBlogCommentList(bid, parent_bcid, offset, config.ascending, include_pinned, config)
        except ExhaustedRetriesError as e:
            if config.verbose:
                print(f"[getAllBlogComments]{config.colorRed}fail to get all comments: {e}")
            return []  # 过于激进?

        if not comment_list:
            return []  # 过于激进?

        for c in comment_list:
            child_num = int(c.get("child_comment_num", 0))
            comment = Comment(
                cid=int(c["bcid"]),
                uid=int(c["uid"]),
                timestamp=parseTime(c['time']),
                content=c["content"],
                reply_count=c["child_comment_num"],
                replies=[],
                is_pinned=bool(c["is_pinned"]),
                pin_order=c["pin_order"],
                c_type='blog'
            )

            if child_num > 0:
                if config.verbose:
                    print(f"[getAllBlogComments]Get replies of bcid{comment.cid}...")
                comment.replies = getAllBlogComments(bid, comment.cid, include_pinned, config)
            all_comments.append(comment)

        if len(comment_list) < config.commentPerReq:
            break
        offset += config.commentPerReq
        time.sleep(random.uniform(*config.commentBatchDelay))
    return all_comments


@startEnd
def sendComment(bid: int, content: str, parent_bcid: int = 0, config: Config = None):
    """发送指定bid的动态评论。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/comment/blogs/{bid}"
    data = {"token": config.token, "parent_bcid": str(parent_bcid), "content": content}
    return _request('post', 'json', "sendComment", url, config=config, data=data)


@startEnd
def getRandomBlogs(config: Config = None) -> list[dict]:
    """获取一组随机动态。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/blog/random?num={config.randomBlogPerReq}"
    return _request('get', 'json', 'getRandomBlogs', url, config=config)['blog_list']


@startEnd
def searchBlogs(term: str, offset: int = 0, bid_desc: bool = True, view_desc: bool = False,
                config: Config = None) -> dict:
    """搜索动态。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/blog/search?search_term={term}&offset={offset}&num={config.searchBlogPerReq}" \
          f"&bid_desc={1 if bid_desc else 0}&view_count_desc={1 if view_desc else 0}"
    return _request('get', 'json', 'searchBlogs', url, config=config)['data']


@startEnd
def toggleBlogLike(bid: int, config: Config = None):
    """切换指定bid的点赞状态。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/blog/like/{bid}"
    return _request('post', 'json', 'toggleBlogLike', url, config=config, data={'token': config.token})['data']


@startEnd
def toggleBlogFavorite(bid: int, config: Config = None):
    """切换指定bid的收藏状态。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/blog/favorite/{bid}"
    return _request('post', 'json', 'toggleBlogFavorite', url, config=config, data={'token': config.token})['data']


@startEnd
def getManageBlogs(offset: int = 0, config: Config = None) -> dict:
    """获取｢动态管理｣内的一组动态(不递归)。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = (
        f"https://{config.APIBase}api/blog/manage-list?num={config.managePerReq}&offset={offset}&_t={int(time.time())}"
        f"&token={config.token}")
    return _request('get', 'json', "getManageBlogs", url, config=config)['data']


@startEnd
def getFavBlogs(offset: int = 0, config: Config = None) -> dict:
    """获取一组收藏的动态(不递归)。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/blog/favorite-list?num={config.managePerReq}&offset={offset}" \
          f"&_t={int(time.time())}&token={config.token}"
    return _request('get', 'json', "getFavBlogs", url, config=config)


@startEnd
def getAllFavBlogs(return_dict: bool = False, config: Config = None) -> Union[list[int], list[dict]]:
    """获取所有收藏的动态。需要token。"""
    if config is None:
        config = getGlobalConfig()
    all_blogs = []
    offset = 0
    while True:
        if offset != 0 and config.verbose:
            print(f"[getAllFavBlogs]curr offset: {offset}")
        try:
            data = getFavBlogs(offset, config)
        except ExhaustedRetriesError as e:
            if config.verbose:
                print(f"[getAllFavBlogs]{config.colorRed}fail to get all favorite blogs: {e}")
            return []
        blog_list = data['data'].get("blog_list", [])
        if not blog_list:
            return []
        for b in blog_list:
            all_blogs.append(b if return_dict else b['bid'])
        if len(blog_list) < config.managePerReq:
            break
        offset += config.managePerReq
        time.sleep(random.uniform(*config.blogBatchDelay))
    return all_blogs


@startEnd
def editBlog(bid: int, tags: list[str] = None, is_gore: bool = None, config: Config = None):
    """编辑指定bid的动态。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/blog/{bid}"
    data = {'token': config.token}
    if is_gore is not None:
        data['is_gore'] = int(is_gore)
    if tags is not None:
        data['tag'] = tags
    return _request('put', 'json', 'editBlog', url, config=config, data=data)


@startEnd
def getBlogCollection(bid: int, config: Config = None) -> dict:
    """获取指定bid的动态合集。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/collection/blogs/{bid}/collection/"
    res = _request('get', 'json', 'getBlogCollection', url, config=config)
    del res['status']
    return res


@startEnd
def reportBlog(bid: int, reason: str, config: Config = None):
    """举报指定bid。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/moderation/blogs/{bid}/report/"
    return _request('post', 'json', 'reportBlog', url, config=config, data={"token": config.token, "reason": reason})
