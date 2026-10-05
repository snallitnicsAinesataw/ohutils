seiga -> 静画

collection -> 合集

blog -> 动态 (n.)

request.is_chat=True <=> 禁alwaysUseToken

window.fetch = function(...args) {console.log('fetch request:', args)};

使用channel_only时，即使动态存在，未登录/不在频道内 会返回BIDError

强行指定 未加入的频道id 发布 会自动 加入 并 订阅: 
 - `ot.blog_api.postBlog('可见性?', '_', channel_id=507, channel_only=True)`会自动加入cid=507

