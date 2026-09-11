import os
from ..core.util import startEnd, _request
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
    """搜索素材。"""
    if config is None:
        config = getGlobalConfig()
    if tags is None:
        tags = []
    params = {
        'search_term': term,
        'offset': offset,
        'num': config.mediaPerReq,
        'media_id_desc': int(not id_asc),
        'media_id_asc': int(id_asc),
        'file_size_desc': int(not size_asc),
        'file_size_asc': int(size_asc),
    }
    if m_type is not None:
        params['media_type'] = m_type
    if tags:
        params['tag'] = '#'.join(tags)
    if spec_uid is not None:
        params['uid'] = spec_uid
    if size_min is not None:
        params['min_file_size'] = size_min
    if size_max is not None:
        params['max_file_size'] = size_max

    url = f"https://{config.APIBase}api/media/search?{urlencode(params, quote_via=quote)}"
    return _request('get', 'json', 'searchMedia', url, config=config)['data']


@startEnd
def downloadMedia(m_id: int, chunk_size: int = 8192, config: Config = None):
    """下载素材。"""
    if config is None:
        config = getGlobalConfig()
    media = getMediaDetail(m_id, config)
    resp = _request('get', 'stream', 'downloadMedia', media['file_url'], config=config, stream=True)
    fp = os.path.join(config.mediaPath, config.mediaName.format(m_id=media["media_id"], ext=media["extension"]))
    with open(fp, "wb") as f:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            f.write(chunk)
