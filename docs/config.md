## 1.3 Config
此文档对应`core\config.py`。`useConfig`在`core\util.py`。

---
## 1.3.1 Config类
ohutils的通用配置类，用于管理所有可配置项。为dataclass。各函数若`config`参数为`None`则会使用全局配置(见1.3.2)或`useConfig(...)`(见1.3.3)设定的配置。

### 1.3.1.1 APIBase, chatAPIBase
`APIBase: str = "api.ottohub.cn/"`
`chatAPIBase: str = "api-chat.ottohub.cn/"`

OTTOHub API 基础地址。一般不用改。**若覆盖，在最后加上**`/`。如`cfg.APIBase='https://example-proxy.com/ottohub/'` 。

### 1.3.1.2 token, alwaysUseToken
`token: str = field(default_factory=str, repr=False)`
`alwaysUseToken: bool = False`

`token` -> 访问令牌。需要`token`的API(带有🔑标记)会使用。调用`auth_api.login()`(2.2.1) 可以获取；调用`auth_api.loginAndSetToken()`(2.2.2) 自动更新全局`token`。

**注意：**`token`**不要转义最后的等号至**`%3d` **，内部会quote。**

`alwaysUseToken`强制在每个请求中加入`token`。


### 1.3.1.3 policy
`policy`控制写`obarc`、`ovarc`时的策略。

> keep策略仅支持{bid}/{vid}、{ver}、{toolver}占位符，出现其它占位符会抛出ValueError。若需使用，请设为keep_after。

> 目前saveVideo()不支持merge策略。


| policy     | 行为                     |
|------------|------------------------|
| keep       | 若本地文件已存在，跳过，不发送请求。     |
| merge      | 将本地文件与更新的数据合并至一个文件。    |
| keep_after | 发送请求，若构造的文件名已存在，丢弃新数据。 |
| override   | 总是覆盖旧文件。               |


### 1.3.1.4 timeout, longTimeout, retries, headers
`timeout: int = 10`
`longTimeout: int = 120`
`retries: int = 3`
`headers: dict = field(default_factory={...}, compare=False)`

`timeout` -> 请求超时秒数。

`longTimeout` -> 在下载、上传大文件时使用的超时。在`vid_api.downloadVideo()`和`misc_api.uploadImage()`使用。

`retries` -> 重试次数。

`headers` -> 请求使用的请求头。不参与比较。

### 1.3.1.5 verbose, useStartEnd
`verbose: bool = False`
`useStartEnd: bool = False`

| verbose | useStartEnd | 行为                        |
|---------|-------------|---------------------------|
| False   | False       | 不打印任何日志。                  |
| True    | False       | 打印日志。                     |
| False   | True        | 只打印start/end。             |
| True    | True        | 打印日志、start/end包含函数参数和返回值。 |

**例子：**

verbose=False, useStartEnd=True:
```text
[13:16:45.460 D][getVideoDetail]start
[13:16:45.705 D][getVideoDetail]end
```

verbose=True, useStartEnd=False:
```text
[13:25:49.450 I][_saveVideo/v1]Get metadata of ov1...
[13:25:49.450 I][getVideoDetail]get https://api.ottohub.cn/api/video/1
[13:25:50.745 I][_saveVideo/v1]Get comments of ov1...
```

verbose=useStartEnd=True:
```text
[14:12:40.850 D][getVideoDetail]start with args vid=12306, config=None
[14:12:40.850 I][getVideoDetail]get https://api.ottohub.cn/api/video/12306
[14:12:41.115 D][getVideoDetail]end with return {'vid': '12306', 'uid': '...
```

### 1.3.1.6 *PerReq

| 项              | 默认值 | 解释                                                                                                                             |
|----------------|-----|--------------------------------------------------------------------------------------------------------------------------------|
| commentPerReq  | 12  | 每次请求获取的**评论**数。在`getAll*Comments()`中使用。                                                                                        |
| blogPerReq     | 12  | 每次请求获取的**动态**数。                                                                                                                |
|                |     | 使用于`getLatestBlog`、`getRandomBlogs`、`searchBlogs`、`getAllChannelContents`、`getAllUserBlogs`、`getAllFavBlogs`、`getManageBlogs`。 |
| channelsPerReq | 12  | 每次请求获取的**频道**数。使用于`getRecChanels()`、`getAllRecChannels()`。                                                                     |
| msgPerReq      | 50  | 每次请求获取的**消息**数。使用于`getIM()`、`getChats()`、`getModeration()`。                                                                    |
| videoPerReq    | 20  | 每次请求获取的**视频**数。使用于`getLatest/Popular/RandomVideos()`。                                                                          |
| tagsPerReq     | 12  | 每次请求获取的**标签**数。在`getPopularTags()`中使用。                                                                                         |
| seigaPerReq    | 20  | 每次请求获取的**静画**数。使用于`getRankedSeiga()`、`getRelatedSeiga()`、`getSeigaByTags()`。                                                   |
| userPerReq     | 18  | 每次请求获取的**用户**数。使用于`getAllFollowers()`、`getAllFollowings()`。                                                                    |
| mediaPerReq    | 12  | 每次请求获取的**素材**数。 在`searchMedia()`中使用。                                                                                           |

### 1.3.1.7 *Path
包含`savePath, indexPath, seigaPath, mediaPath, videoPath, chunkPath`。默认值均为`'.\\'`。

`savePath` -> 保存`obarc`、`ovarc`的路径。

`indexPath` -> 保存索引文件JSON的路径。

`seigaPath, mediaPath, videoPath` -> 保存静画、素材、**下载的视频文件**(downloadVideo)路径。

`chunkPath` -> `.obchk`文件保存位置。


### 1.3.1.8 *Name
包含`obarcName, ovarcName, seigaName, mediaName, videoName, SQLName`。

| 项             | 默认值                                 | 解释                    |
|---------------|-------------------------------------|-----------------------|
| obarcName     | `{bid}`                             | `.obarc`文件名。支持占位符(见)。 |
| ovarcName     | `{vid}`                             | `.ovarc`文件名。支持占位符。    |
| seigaName     | `sid{sid}_p{page}.jpg`              | 下载的静画文件名。支持占位符。       |
| mediaName     | `m_id{m_id}.{ext}`                  | 素材文件名。支持占位符。          |
| videoName     | `{vid}_ou{uid}.mp4`                 | 下载的视频文件名。支持占位符。       |
| SQLName       | `ohutils.db`                        | 导出数据库的文件名。            |
| blogChunkName | `chk_{start}_{end}_fl-{flag}.obchk` | `.obchk`文件名。          |

### 1.3.1.9 *IdxName, indexName, *BlobName
包含`indexName, userCommentIdxName, OBCCommentIdxName, obarcBlobName, ovarcBlobName`。

| 项                  | 默认值                       | 解释                                 |
|--------------------|:--------------------------|------------------------------------|
| indexName          | `.\\`                     | `buildBlogIndex()`生成的动态的索引JSON文件名。 |
| userCommentIdxName | `comment_index_user.json` | 动态评论的索引JSON文件名。以uid为键。             |
| OBCCommentIdxName  | `comment_index_obc.json`  | 动态评论的索引JSON文件名。以bcid为键。            |
| obarcBlobName      | `ob*`                     | glob扫描时使用的通配符。                     |
| ovarcBlobName      | `ov*`                     | glob扫描时使用的通配符。                     |

### 1.3.1.10 *Delay
包含`stageDelay, pagingDelay, retryDelay`。

**格式：** 指定上下界`(float, float)`。单位：**秒**。

`stageDelay` -> 不同阶段(如 元数据->评论->弹幕->封面->视频流)之间的间隔。默认`(1.0, 1.0)`。

`pagingDelay` -> (评论等需要翻页的数据) 翻页的间隔。默认`(0.4, 0.8)`。

`retryDelay` -> 重试间隔。默认`(1.0, 3.0)`。


### 1.3.1.11 password, salt
> **不要使用默认值。**

`password: bytes = field(default_factory=lambda: b'example_password', repr=False, compare=False)`

`salt: bytes = field(default_factory=lambda: b'0123456789abcdef', repr=False, compare=False)`

加密(AES-256)使用的配置项。不参与比较，不打印。于`arc.buildChunk()`内使用。


### 1.3.1.12 ascending
`ascending: bool = False`

`ascending` -> 排序方式。使用于`getAll*Comments()`、`getChannelPins()`、`get(All)RecChannels()`、`getIM()`。

### 1.3.1.13 gore
`gore: bool = True`

是否请求4000+内容。使用于`getLatestBlog()`、`getPopularTags()`、`getRankedSeiga()`、`getRelatedSeiga()`、`getSeigaByTags()`。

**后三个在禁止访问时会抛出**`GoreNotAllowedError`。


### 1.3.1.14 lookupTableBias
`lookupTableBias: int = 32`

.obchk文件内部查找表偏移。一般不用改。


### 1.3.1.15 richLog
`richLog: bool = True`

是否启用彩色日志。禁用的情况适合写入log文件 或 输出至不支持ANSI转义的终端。

### 1.3.1.16 chunkSize
`chunkSize: int = 8192`

块大小。单位：**字节**。使用于`downloadVideo()`、`downloadMedia()`。

### 1.3.1.17 fromDict()
`@classmethod fromDict(cls, d: dict) -> Config`

从字典导入配置。

例子：
```python
import ohutils
cfg = ohutils.Config.fromDict({'verbose': True, 'policy': 'keep'})
assert cfg.verbose
assert cfg.policy == 'keep'
```

### 1.3.1.18 fromYaml()
`@classmethod fromYaml(cls, fp: str) -> Config`

从YAML文件导入配置。如果.yml中的值是如`${VAR}`的占位符，替换为环境变量。环境变量不存在时，保留原字符串。(`token`等字段可以使用)。

例子：
```yaml
# config.yml
token: ${OH_TOKEN}
savePath: ./archive
verbose: true
timeout: 30
```
```python
import ohutils

cfg = ohutils.Config.fromYaml("config.yml")
print(config.token)      # "WWdPkyQJ...MD0="
assert config.savePath == "./archive"
assert config.verbose
assert cfg.timeout == 30
```

### 1.3.1.19 replace()
`replace(self, **changes) -> Config`

返回一个替换了指定项、值的`Config`对象。等价于`dataclasses.replace(config, **changes)`。

---
## 1.3.2 setGlobalConfig(), getGlobalConfig()
`setGlobalConfig(config: Config) -> None` `getGlobalConfig() -> Config`

设置、获取全局配置。

## 1.3.3 useConfig()
`@contextmanager useConfig(config: Config) -> Generator[Config, None, None]`

使用给定的config。此函数的优先级低于在函数调用时显式传递的`config=...`参数，但高于`setGlobalConfig()`。

**在上下文内设置**`setGlobalConfig()` **无效。不支持嵌套with。**

例子：
```python
import ohutils

cfg1 = ohutils.Config()
cfg2 = ohutils.Config(alwaysUseToken=True)
cfg3 = ohutils.Config(verbose=True)
ohutils.setGlobalConfig(cfg1)

ohutils.blog_api.getBlogDetail(12306)  # 使用cfg1
with ohutils.useConfig(cfg2):
    ohutils.blog_api.getBlogDetail(12306)  # 使用cfg2
    ohutils.blog_api.getBlogDetail(12306, config=cfg3)  # 使用cfg3
    ohutils.setGlobalConfig(cfg3)          # 无效
    ohutils.blog_api.getBlogDetail(12306)  # 还是cfg2
```