import json
from collections import Counter
import ottosave
from pprint import pprint
from random import shuffle

# ottosave.build_index()
# ottosave.indexes.buildBlogIndex()
index = ottosave.arc.loadBlogIndex()
# bid: {uid, ts, c_len, ver, size, title}
# 按评论数排序，找出最热动态
# top = sorted(index.values(), key=lambda x: x['c_len'], reverse=True)[:10]
# 按时间排序，画出社区活跃曲线
# timeline = sorted(index.values(), key=lambda x: x['ts'])
# 按作者分组，找到最活跃用户
# uid_counts = Counter(v['uid'] for v in index.values())
# 找出所有幽灵动态（title 为空或 content 为空）
# ghosts = [bid for bid, v in index.items() if v.get('title', '') == '']

# ghosts = [int(bid) for bid, v in index.items() if (v.get('ts', 946656000) == 946656000 and int(bid)<=10000)]
# shuffle(ghosts)
# print(str(ghosts).replace(', ',';'))
# print(ottosave.indexes.loadObarcMerged(25164))
# print(Counter(v['ver'] for v in index.values()))
top = sorted(index.values(), key=lambda x: x['c_len'], reverse=True)
top = [(v['bid'], v['c_len']) for v in top if v.get('ts', 946656000) == 946656000][:10]
print(top)
exit()
all_ = [bid for bid, v in index.items() if v.get('uid', 0) == 5337]
for b in all_:
    print(f"{b}: {ottosave.obarc.loadObarcMerged(int(b)).title}")
