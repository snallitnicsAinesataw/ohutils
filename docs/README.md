# OHUtils
[OTTOHub](https://www.ottohub.cn/) 数据工具集。

[文档目录](index.md)

---
## 功能
- API封装
- 动态/视频/静画等数据获得
- 多格式存档(.obarc, .obchk; .db)
- 聊天室客户端

## 安装
```commandline
pip install ohutils
```

## 示例
动态数据获取:
```python
import ohutils
blog: dict = ohutils.blog_api.getBlogRaw(4824)
print(blog.get('title'))  # 'OTTOHUB审核细则'
```