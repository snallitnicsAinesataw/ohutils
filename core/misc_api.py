from .util import _requestJson, startEnd, _requestContent
from .config import Config, getGlobalConfig
import requests


@startEnd
def getLegalDocsRaw(config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    url = "https://api.ottohub.cn/api/system/legal-documents/"
    return _requestJson('getLegalDocsRaw', url, config)


@startEnd
def getTermsOfService(config: Config = None) -> str:
    if config is None:
        config = getGlobalConfig()
    url = getLegalDocsRaw(config)['data']['documents']['terms_of_service_url']
    return _requestContent('getTermsOfService', url, config).decode('utf-8')


@startEnd
def getPrivacyPolicy(config: Config = None) -> str:
    if config is None:
        config = getGlobalConfig()
    url = getLegalDocsRaw(config)['data']['documents']['privacy_policy_url']
    return _requestContent('getPrivacyPolicy', url, config).decode('utf-8')


@startEnd
def getReviewSpec(config: Config = None) -> str:
    if config is None:
        config = getGlobalConfig()
    url = getLegalDocsRaw(config)['data']['documents']['platform_content_review_specification_url']
    return _requestContent('getReviewSpec', url, config).decode('utf-8')


@startEnd
def getSlideshowRaw(config: Config = None) -> dict:
    if config is None:
        config = getGlobalConfig()
    return _requestJson('getSlideshowRaw', 'https://api.ottohub.cn/api/system/slideshow/', config)
