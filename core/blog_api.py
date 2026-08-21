from .util import startEnd, Comment, parseTime, _request, APIError
from .exception import ExhaustedRetriesError
from .config import Config, getGlobalConfig
import requests
import time
from typing import List, Union
import random


@startEnd
def getBlogRaw(bid: int, config: Config = None) -> dict:
    """获取指定bid的动态数据。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/blog/{bid}/detail/"
    return _request('get', 'json', 'getBlogRaw', url, config)


@startEnd
def getLatestBlogRaw(offset: int = 0, config: Config = None) -> dict:
    """获取最近的动态。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/blog/latest?offset={offset}&num={config.latestBlogPerReq}&is_gore={int(config.gore)}"
    return _request('get', 'json', 'getLatestBlogRaw', url, config)


@startEnd
def getBlogCommentListRaw(bid, parent_bcid=0, offset=0, config: Config = None) -> dict:
    """拉取指定bid的一组父评论(不递归)。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/comment/blogs/{bid}?parent_bcid={parent_bcid}&offset={offset}&num={config.commentPerReq}"
    return _request('get', 'json', 'getBlogCommentListRaw', url, config)


@startEnd
def getAllBlogComments(bid: int, parent_bcid: int = 0, config: Config = None) -> List[Comment]:
    """递归拉取指定bid的所有评论。"""
    if config is None:
        config = getGlobalConfig()
    all_comments = []
    offset = 0
    while True:
        if offset != 0 and config.verbose:
            print(f"[getAllBlogComments]curr offset: {offset}")

        try:
            data = getBlogCommentListRaw(bid, parent_bcid, offset, config)
        except ExhaustedRetriesError as e:
            if config.verbose:
                print(f"[getAllBlogComments]{config.colorRed}fail to get all comments: {e}")
            return []  # 过于激进?

        comment_list = data['data'].get("comment_list", [])
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
                comment.replies = getAllBlogComments(bid, comment.cid, config)

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
    return _request('post', 'json', "sendComment", url, config, data)


@startEnd
def getRandomBlogRaw(config: Config = None) -> dict:
    """获取一组随机动态。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/blog/random?num={config.randomBlogPerReq}"
    return _request('get', 'json', 'getRandomBlogRaw', url, config)


@startEnd
def searchBlogsRaw(term: str, offset: int = 0, bid_desc: bool = True, view_desc: bool = False,
                   config: Config = None) -> dict:
    """搜索动态。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/blog/search?search_term={term}&offset={offset}&num={config.searchBlogPerReq}" \
          f"&bid_desc={1 if bid_desc else 0}&view_count_desc={1 if view_desc else 0}"
    return _request('get', 'json', 'searchBlogsRaw', url, config)


@startEnd
def toggleBlogLike(bid: int, config: Config = None):
    """切换指定bid的点赞状态。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/blog/like/{bid}"
    return _request('post', 'json', 'toggleBlogLike', url, config, {'token': config.token})


@startEnd
def toggleBlogFavorite(bid: int, config: Config = None):
    """切换指定bid的收藏状态。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/blog/favorite/{bid}"
    return _request('post', 'json', 'toggleBlogFavorite', url, config, {'token': config.token})


@startEnd
def getManageBlogsRaw(offset: int = 0, config: Config = None) -> dict:
    """获取｢动态管理｣内的一组动态(不递归)。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = (
        f"https://{config.APIBase}api/blog/manage-list?num={config.managePerReq}&offset={offset}&_t={int(time.time())}"
        f"&token={config.token}")
    return _request('get', 'json', "getManageBlogsRaw", url, config)


@startEnd
def getFavBlogsRaw(offset: int = 0, config: Config = None) -> dict:
    """获取一组收藏的动态(不递归)。需要token。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/blog/favorite-list?num={config.managePerReq}&offset={offset}" \
          f"&_t={int(time.time())}&token={config.token}"
    return _request('get', 'json', "getFavBlogsRaw", url, config)


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
            data = getFavBlogsRaw(offset, config)
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
    return _request('put', 'json', 'editBlog', url, config, data)


@startEnd
def getBlogCollectionRaw(bid: int, config: Config = None):
    """获取指定bid的动态合集。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/collection/blogs/{bid}/collection/"
    return _request('get', 'json', 'getBlogCollectionRaw', url, config)