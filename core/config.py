from dataclasses import dataclass, field, fields


@dataclass
class Config:
    password: bytes = field(default_factory=lambda: b'example_password', repr=False, compare=False)
    salt: bytes = field(default_factory=lambda: b'0123456789abcdef', repr=False, compare=False)

    colorRed: str = field(default_factory=lambda: '\033[38;5;196m', repr=False, compare=False)
    colorYellow: str = field(default_factory=lambda: '\033[38;2;244;177;2m', repr=False, compare=False)
    colorGray: str = field(default_factory=lambda: '\033[38;5;240m', repr=False, compare=False)
    colorMagenta: str = field(default_factory=lambda: '\033[95m', repr=False, compare=False)

    headers: dict = field(default_factory=lambda: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://api.ottohub.cn/',
        'Connection': 'keep-alive'
    }, compare=False)
    token: str = field(default_factory=str, repr=False)
    alwaysUseToken: bool = False

    timeout: int = 10
    retries: int = 3
    verbose: bool = False
    noStartEnd: bool = True

    commentPerReq: int = 12
    subCommentPerReq: int = 6
    userBlogPerReq: int = 20
    latestBlogPerReq: int = 12
    channelsPerReq: int = 12
    msgPerReq: int = 50
    modLogPerReq: int = 20
    videoPerReq: int = 20

    savePath: str = 'D:\\_ARCHIVE\\DISP\\'  # should be .\
    indexPath: str = 'E:\\pyfile\\small-projects\\ottosave\\'
    policy: str = 'merge'
    fileName: str = "ob%i.obarc"
    regexName: str = "ob*.obarc"
    indexName: str = "archive_index.json"
    userCommentIdxName: str = "comment_index_user.json"
    OBCCommentIdxName: str = "comment_index_obc.json"

    chunkPath: str = 'D:\\_ARCHIVE\\DISP\\'  # should be .\
    blogChunkName: str = "chk_%i_%i_fl-%i.obchk"
    lookupTableBias: int = 32

    sorting: str = "created_at"
    ascending: bool = False

    @classmethod
    def fromDict(cls, d: dict):
        """从字典更新配置"""
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in d.items() if k in valid_keys and v is not None}
        return cls(**filtered)


_DEFAULT_CONFIG = Config()


def setGlobalConfig(config: Config):
    global _DEFAULT_CONFIG
    _DEFAULT_CONFIG = config


def getGlobalConfig() -> Config:
    return _DEFAULT_CONFIG

