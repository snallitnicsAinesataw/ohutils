# OHUtils
[OTTOHub](https://www.ottohub.cn/) 数据工具集。

---
## 功能
- API封装
- 动态/视频/静画等数据获得
- 多格式存档(.obarc, .obchk; .db)
- 聊天室客户端
---
## 安装
```commandline
pip install ohutils
```
---
## 示例
动态数据获取:
```python
import ohutils
blog: dict = ohutils.blog_api.getBlogRaw(4824)
print(blog.get('title'))  # 'OTTOHUB审核细则'
```

视频数据获取:
```python
import ohutils
print(ohutils.vid_api.getAllDanmaku(1917))
# [Danmaku(danmaku_id=67406, text='bakabaka', ...), 
#  Danmaku(danmaku_id=1605, text='?之妖精', ...), 
#  Danmaku(danmaku_id=1604, text='funky', ...)]
```

静画下载:
```python
import ohutils
ohutils.seiga_api.downloadSeiga(8)
```

聊天室客户端:
```python
import ohutils
client, _ = ohutils.chat_api.connectChat(threaded=True)
client.sendMessage('Message from OHUtils')
client.close()
```

存档:
```python
import ohutils
ohutils.arc.archiveBlog(52553)
# ('.\\ob52553.obarc', True)
```
