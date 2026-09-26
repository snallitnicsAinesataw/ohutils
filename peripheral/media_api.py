import os
from ..core.util import startEnd, _request, logger
from ..core.config import Config, getGlobalConfig
import requests


@startEnd
def getMediaDetail(m_id: int, config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/media/{m_id}"
    return _request('get', 'json', 'getMediaDetail', url, config=config)['data']['media_list'][0]


@startEnd
def searchMedia(term: str, offset: int = 0, m_type: str = None, tags: list[str] = None,
                id_asc: bool = False, size_asc: bool = True, spec_uid: int = None,
                size_min: int = None, size_max: int = None, config: Config = None) -> dict:
    """搜索素材。
    m_type支持的常量: ohutils.MT_*"""
    if config is None:
        config = getGlobalConfig()
    if tags is None:
        tags = []
    params = {
        'search_term': term,
        'offset': offset,
        'num': config.mediaPerReq,
        'media_id_desc': int(not id_asc),
        'media_id_asc': int(id_asc),  # 那个神秘前端这两个开关竟然能同时勾选
        'file_size_desc': int(not size_asc),
        'file_size_asc': int(size_asc),  # 这俩也是，虽然我没测试同时勾选会怎么样
    }
    if m_type is not None:
        params['media_type'] = m_type
    if tags:
        params['tag'] = ''.join('#'+t for t in tags)
    if spec_uid is not None:
        params['uid'] = spec_uid
    if size_min is not None:
        params['min_file_size'] = size_min
    if size_max is not None:
        params['max_file_size'] = size_max

    url = f"https://{config.APIBase}api/media/search?{urlencode(params, quote_via=quote)}"
    return _request('get', 'json', 'searchMedia', url, config=config)['data']


@startEnd
def downloadMedia(m_id: int, config: Config = None):
    """下载素材。"""
    if config is None:
        config = getGlobalConfig()
    suffix = '.ohu-downloading'
    media = getMediaDetail(m_id, config)
    resp = _request('get', 'stream', 'downloadMedia', media['file_url'], config=config, stream=True)
    fp = os.path.join(config.mediaPath, config.mediaName.format(m_id=media["media_id"], ext=media["extension"]) + suffix)
    fp_new = fp
    with open(fp, "wb") as f:
        for chunk in resp.iter_content(chunk_size=config.chunkSize):
            f.write(chunk)
    if fp.endswith(suffix):
        fp_new = fp[:-len(suffix)]
    os.replace(fp, fp_new)
    logger.info(f'[downloadMedia]media downloaded: {fp_new}')
