# OHUtils 导出文件定义

## SQLite数据表定义 (.db)

### 用户元数据: oh_user_v1
```sql
CREATE TABLE oh_user_v1 (
uid INTEGER PRIMARY KEY NOT NULL,
name TEXT,
intro TEXT,
create_ts INTEGER,
sex TEXT,
honour TEXT,
exp INTEGER,
avatar BLOB,
cover_h BLOB,
cover_v BLOB,
video INTEGER,
blog INTEGER,
seiga INTEGER,
media INTEGER,
follow INTEGER,
fan INTEGER)
```

### 动态数据: oh_blog_v1
```sql
CREATE TABLE oh_blog_v1 (
bid INTEGER PRIMARY KEY NOT NULL,
uid INTEGER,
pub_ts INTEGER,
arc_ts INTEGER,
channel INTEGER,
like INTEGER,
fav INTEGER,
view INTEGER,
attached_vid INTEGER,
copyright_type INTEGER,
blog_type INTEGER,
comment_count INTEGER,
title TEXT,
content TEXT,
tags TEXT,
gore INTEGER)
```

### 动态评论数据: oh_obc_v1
```sql
CREATE TABLE oh_obc_v1 (
bcid INTEGER PRIMARY KEY NOT NULL,
bid INTEGER,
uid INTEGER,
parent_bcid INTEGER DEFAULT 0,
pub_ts INTEGER,
content TEXT,
reply_count INTEGER DEFAULT 0,
pin_order INTEGER DEFAULT 0)
```

### 视频评论数据: oh_ovc_v1
```sql
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
uid INTEGER,
target_uid INTEGER,
PRIMARY KEY (uid, target_uid)
)
```