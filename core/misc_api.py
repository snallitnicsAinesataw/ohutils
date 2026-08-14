from .util import startEnd, _request
from .config import Config, getGlobalConfig
import requests


@startEnd
def getLegalDocsRaw(config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = f"{config.APIBase}api/system/legal-documents/"
    return _request('get', 'json', 'getLegalDocsRaw', url, config)


@startEnd
def getTermsOfService(config: Config = None) -> str:
    if config is None:
        config = getGlobalConfig()
    url = getLegalDocsRaw(config)['data']['documents']['terms_of_service_url']
    return _request('get', 'content', 'getTermsOfService', url, config).decode('utf-8')


@startEnd
def getPrivacyPolicy(config: Config = None) -> str:
    if config is None:
        config = getGlobalConfig()
    url = getLegalDocsRaw(config)['data']['documents']['privacy_policy_url']
    return _request('get', 'content', 'getPrivacyPolicy', url, config).decode('utf-8')


@startEnd
def getReviewSpec(config: Config = None) -> str:
    if config is None:
        config = getGlobalConfig()
    url = getLegalDocsRaw(config)['data']['documents']['platform_content_review_specification_url']
    return _request('get', 'content', 'getReviewSpec', url, config).decode('utf-8')


@startEnd
def getSlideshowRaw(config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    return _request('get', 'json', 'getSlideshowRaw', f'{config.APIBase}api/system/slideshow/', config)
