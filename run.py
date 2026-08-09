from ottosave import *
from random import randint, shuffle
import time
import requests
import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="Ottosave args")
    parser.add_argument("--s", type=int, help="起始bid", metavar='start', required=True)
    parser.add_argument("--e", type=int, help="结束bid", metavar='end', required=True)
    parser.add_argument("--policy", choices=["keep", "merge", "override"], default="keep", help="策略")
    parser.add_argument("-R", action='store_true', default=False, help="反转顺序？")
    return parser.parse_args()


args = parse_args()
config = Config.fromDict({'verbose': True, 'policy': args.policy, 'retries': 2})
config.noStartEnd = False
setGlobalConfig(config)


def main(execute=None):
    print('[main]Hello!')
    start = args.s
    L = args.e + 2 - start
    result = [range(i, min(i + 10, start - 1 + L)) for i in range(start, start + L, 10)]
    # print(result)
    # time.sleep(100)
    # result = [[2,3,4,5,6,7,8,9,10,15,18,19,20,21,22,23,24,31,43,44,45,46,47,48,51,52,55,82,96,98,99]]
    # result = [[int(t['bid']) for t in user_api.getAllUserBlog(671)]]
    # result = [[int(t['bid']) for t in getAllUserBlog(11144)]]
    # result = [[int(t['bid']) for t in user_api.getAllUserBlog(20032)]]
    # result = [[5781,5794,5830,5836,5863,5869,6943,6944,6973,7027,7040,7803]]
    # result = [[8256,8905,9625]]
    # shuffle(result)
    if args.R:
        result = result[::-1]
    # print(result, '\n')
    for ids_ in result:
        if len(list(ids_)) == 0:
            continue
        print(f"[main]***** Download ob{ids_[0]}~ob{ids_[-1]} *****")
        get_list = []
        for id_ in ids_:

            if id_ == 36706:
                continue

            for att in range(10):
                try:
                    _, is_net = arc.archiveBlog4(id_)
                    if is_net:
                        time.sleep(randint(6, 8))
                    get_list.append(is_net)
                    break
                except (requests.exceptions.RequestException, TimeoutError, ConnectionError) as e:
                    time.sleep(30)
                    print(f"[main]{config.colorYellow}({att+1}/10) Retry ob{id_}: {e}\033[0m")
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    print(f"[main]{config.colorRed}Not network exception, skip ob{id_}: {e}\033[0m")
                    get_list.append(True)
                    break  # 不重试
                get_list.append(True)
        if any(get_list):
            slp = randint(5, 8) * min(get_list.count(True), 12)
            slp = slp+randint(-20, 10) if slp >= 25 else slp
            print(f"[main]***** Resting for {slp} secs... *****")
            time.sleep(slp)

    if execute is not None:
        for _ in range(132):
            exec(execute)
            time.sleep(60)


if __name__ == '__main__':
    main(
        "__import__('os').system('shutdown /s /t 10')"
    )
    # print(search(r'道理'))
    # archiveBlog3(44395, path=path, policy='override')
    # print(getBlogRaw(3))
    # print(getBlogRaw(43269))
    # print(loadObarc(path + 'ob149.obarc'))
    # print(getCommentListRaw(43269))
    # print(loadObarc3(path + 'ob35738.obarc'))
    # print(getAllUserBlog(671))
    # archiveBlog3(43269, path=path, policy='merge')
    # key = genKey(b"example_pswd", salt=b'0123456789abcdef')
    # cipher = encrypt(key, b'test_text')
    # key = genKey(b' example_pswd', salt=b'0123456789abcdef')
    # print(cipher,'\n',decrypt(key, cipher))
    # buildChunk(3, 3, path=e_path, flags=1, key=key)
    # buildChunk(1, 10000, path=e_path, flags=1, key=key)
    # print(loadChunk(e_path + "chk_1_10000_fl-1.obchk", key=key))
    # buildChunk(3, 3, path=e_path, flags=1, key=key, lookup_bias=64)
    # print(loadChunk(e_path + "chk_3_3_fl-1.obchk", key=key))
    ...
