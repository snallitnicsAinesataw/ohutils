from dataclasses import dataclass, field, fields, replace
import yaml
import os


class _IConfig:
    # 内部配置，存一些不需要暴露的字段。以及它包含全局Config()。
    # 曾经有想过｢啊我把这个参数放在config里吧、啊不放了吧还是｣，但我忘记是什么了。
    def __init__(self):
        self.curr_cfg = Config()


@dataclass
class Config:
    APIBase: str = "api.ottohub.cn/"
    chatAPIBase: str = "api-chat.ottohub.cn/"

    password: bytes = field(default_factory=lambda: b'example_password', repr=False, compare=False)
    salt: bytes = field(default_factory=lambda: b'0123456789abcdef', repr=False, compare=False)

    headers: dict = field(default_factory=lambda: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://api.ottohub.cn/',
        'Connection': 'keep-alive'
    }, compare=False)
    token: str = field(default_factory=str, repr=False)
    alwaysUseToken: bool = False

    colorRed: str = field(default_factory=lambda: '\033[38;5;196m', repr=False, compare=False)
    colorYellow: str = field(default_factory=lambda: '\033[38;2;244;177;2m', repr=False, compare=False)
    colorGray: str = field(default_factory=lambda: '\033[38;5;240m', repr=False, compare=False)
    _colorClear: str = field(default_factory=lambda: '\033[0m', repr=False, compare=False)

    timeout: int = 10
    uploadTimeout: int = 120
    retries: int = 3
    verbose: bool = False
    useStartEnd: bool = False

    commentPerReq: int = 12
    subCommentPerReq: int = 6
    userBlogPerReq: int = 20
    latestBlogPerReq: int = 12
    randomBlogPerReq: int = 12
    searchBlogPerReq: int = 12
    channelsPerReq: int = 12
    managePerReq: int = 12
    msgPerReq: int = 50
    modLogPerReq: int = 20
    videoPerReq: int = 20
    tagsPerReq: int = 12
    seigaPerReq: int = 20
    userPerReq: int = 18

    savePath: str = 'D:\\_ARCHIVE\\DISP\\'  # should be .\
    indexPath: str = 'E:\\pyfile\\small-projects\\ohutils\\'
    policy: str = 'merge'
    fileName: str = "ob{bid}.obarc"
    blobName: str = "ob*.obarc"
    indexName: str = "archive_index.json"
    userCommentIdxName: str = "comment_index_user.json"
    OBCCommentIdxName: str = "comment_index_obc.json"
    seigaPath: str = 'D:\\_ARCHIVE\\SEIGA\\'
    seigaName: str = "sid{sid}_p{page}.jpg"

    SQLName: str = "ohutils.db"
    useSQL: bool = False

    chunkPath: str = 'D:\\_ARCHIVE\\DISP\\'  # should be .\
    blogChunkName: str = "chk_{start}_{end}_fl-{flag}.obchk"
    lookupTableBias: int = 32

    sorting: str = "created_at"
    ascending: bool = False
    gore: bool = True

    blogToCommentDelay: tuple[float, float] = (1.0, 1.0)
    commentBatchDelay: tuple[float, float] = (0.0, 2.0)
    seigaDelay: tuple[float, float] = (0.5, 1.0)
    blogBatchDelay: tuple[float, float] = (0.4, 0.8)
    retryDelay: tuple[float, float] = (0.7, 1.1)
    userBatchDelay: tuple[float, float] = (0.6, 0.9)

    __richLog: bool = field(default_factory=lambda: True, repr=False)
    __orig_colors: tuple = field(default_factory=lambda: None, repr=False, compare=False)

    @classmethod
    def fromDict(cls, d: dict):
        """从字典导入配置。"""
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in d.items() if k in valid_keys and v is not None}
        return cls(**filtered)

    @classmethod
    def fromYaml(cls, fp: str):
        """从.yml文件导入配置。"""
        with open(fp, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 如果.yml中包含如${VAR}的占位符，替换为环境变量
        for key, value in data.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                data[key] = os.environ.get(env_var, value)
        return cls(**data)

    def replace(self, **changes):
        """临时替换配置。其实就是dataclasses.replace()。"""
        rich_log = changes.pop('richLog', None)
        new_ = replace(self, **changes)
        if rich_log is not None:
            new_.richLog = rich_log
        return new_

    def _copy(self):
        return replace(self)

    @property
    def richLog(self) -> bool:
        return self.__richLog

    @richLog.setter
    def richLog(self, value: bool):
        self.__richLog = value
        if not value:
            # 设置为False时，覆盖color*
            self.__orig_colors = (self.colorRed, self.colorGray, self.colorYellow, self._colorClear)
            self.colorRed = self.colorGray = self.colorYellow = self._colorClear = ''
        else:
            self.colorRed, self.colorGray, self.colorYellow, self._colorClear = self.__orig_colors


_DEFAULT_CONFIG = _IConfig()


def setGlobalConfig(config: Config):
    _DEFAULT_CONFIG.curr_cfg = config


def getGlobalConfig() -> Config:
    return _DEFAULT_CONFIG.curr_cfg


def _getIConfig() -> _IConfig:
    return _DEFAULT_CONFIG

