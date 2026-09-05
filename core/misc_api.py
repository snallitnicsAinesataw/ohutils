from .util import startEnd, _request
from .config import Config, getGlobalConfig
import requests


@startEnd
def getLegalDocsURL(config: Config = None) -> dict:
    """获取法律文件URL。"""
    if config is None:
        config = getGlobalConfig()
    url = f"https://{config.APIBase}api/system/legal-documents/"
    return _request('get', 'json', 'getLegalDocsURL', url, config=config)['data']['documents']


@startEnd
def getTermsOfService(config: Config = None) -> str:
    """获取｢用户协议｣文档。"""
    if config is None:
        config = getGlobalConfig()
    url = getLegalDocsURL(config)['terms_of_service_url']
    return _request('get', 'content', 'getTermsOfService', url, config=config).decode('utf-8')


@startEnd
def getPrivacyPolicy(config: Config = None) -> str:
    """获取｢隐私政策｣文档。"""
    if config is None:
        config = getGlobalConfig()
    url = getLegalDocsURL(config)['privacy_policy_url']
    return _request('get', 'content', 'getPrivacyPolicy', url, config=config).decode('utf-8')


@startEnd
def getReviewSpec(config: Config = None) -> str:
    """获取｢平台内容审核规范｣文档。"""
    if config is None:
        config = getGlobalConfig()
    url = getLegalDocsURL(config)['platform_content_review_specification_url']
    return _request('get', 'content', 'getReviewSpec', url, config=config).decode('utf-8')


@startEnd
def getSlideshow(config: Config = None) -> list:
    """获取首页轮播图。"""
    if config is None:
        config = getGlobalConfig()
    url = f'https://{config.APIBase}api/slideshow/active/'
    return _request('get', 'json', 'getSlideshow', url, config=config)['data']['slides']
