# 附 I: 导出文件定义

## SQLite数据表定义 (.db)

### 用户元数据: oh_user_v1
```sql
CREATE TABLE oh_user_v1 (
uid INTEGER PRIMARY KEY NOT NULL,
name TEXT,  -- 用户名。
intro TEXT,  -- 简介。
create_ts INTEGER,  -- 创建账号时间戳。
arc_ts INTEGER,  -- 数据收集时间戳。
sex TEXT,  -- 性别。
honour TEXT,  -- 称号 (不包含｢吉吉国民｣)。
exp INTEGER,  -- 经验。
avatar BLOB,  -- 头像二进制数据。
cover_h BLOB,  -- 横版封面二进制数据。
cover_v BLOB,  -- 竖版封面二进制数据。
video INTEGER,  -- 视频投稿数。
blog INTEGER,  -- 动态投稿数。
seiga INTEGER,  -- 静画投稿数。
media INTEGER,  -- 素材投稿数。
follow INTEGER,  -- 关注数。
fan INTEGER,   -- 粉丝数。
avatar_url TEXT,   -- 头像URL。
cover_h_url TEXT,  -- 横版封面URL。
cover_v_url TEXT,  -- 竖版封面URL。
CHECK (  -- 此约束表: 二进制数据和URL互斥。
((avatar IS NULL AND avatar_url IS NOT NULL) OR (avatar IS NOT NULL AND avatar_url IS NULL)) AND
((cover_h IS NULL AND cover_h_url IS NOT NULL) OR (cover_h IS NOT NULL AND cover_h_url IS NULL)) AND
((cover_v IS NULL AND cover_v_url IS NOT NULL) OR (cover_v IS NOT NULL AND cover_v_url IS NULL)))
)
```

### 动态数据: oh_blog_v1
```sql
CREATE TABLE oh_blog_v1 (
bid INTEGER PRIMARY KEY NOT NULL,
uid INTEGER,
pub_ts INTEGER,    -- 发布时间戳。
arc_ts INTEGER,    -- 数据收集时间戳。
channel INTEGER,   -- 频道cid。
like INTEGER,   -- 点赞数。
fav INTEGER,    -- 冷藏数。
view INTEGER,   -- 浏览数。
attached_vid INTEGER,  -- 关联视频vid。
copyright_type INTEGER,  -- 来自API，未知用途作保留。
blog_type INTEGER,    -- 来自API，未知用途作保留。
comment_count INTEGER,  -- 评论数。
title TEXT,
content TEXT,
tags TEXT,    -- 标签，以","分隔。
gore INTEGER   -- 是否为4000+内容。
)
```

### 动态评论数据: oh_obc_v1
```sql
CREATE TABLE oh_obc_v1 (
bcid INTEGER PRIMARY KEY NOT NULL,
bid INTEGER,
uid INTEGER,
parent_bcid INTEGER DEFAULT 0,  -- 父评论id。
pub_ts INTEGER,    -- 发布时间戳。
content TEXT,
reply_count INTEGER DEFAULT 0,  -- 回复数。
pin_order INTEGER DEFAULT 0  -- 置顶顺序, 0表｢未置顶｣。
)
```

### 视频评论数据: oh_ovc_v1
```sql
-- 含义同oh_obc_v1。
CREATE TABLE oh_ovc_v1 (
vcid INTEGER PRIMARY KEY NOT NULL,
vid INTEGER,
uid INTEGER,
parent_vcid INTEGER DEFAULT 0,
pub_ts INTEGER,
content TEXT,
reply_count INTEGER DEFAULT 0,
pin_order INTEGER DEFAULT 0)
```

### 静画评论数据: oh_osc_v1
```sql
-- 含义同oh_obc_v1。
CREATE TABLE oh_osc_v1 (
scid INTEGER PRIMARY KEY NOT NULL,
sid INTEGER,
uid INTEGER,
parent_scid INTEGER DEFAULT 0,
pub_ts INTEGER,
content TEXT,
reply_count INTEGER DEFAULT 0)
```

### 关注信息: oh_follow_v1
```sql
CREATE TABLE oh_follow_v1 (
uid INTEGER,  -- 关注者uid
target_uid INTEGER,  -- 被关注者uid
PRIMARY KEY (uid, target_uid)
)
```