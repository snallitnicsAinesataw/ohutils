import glob, re
# from collections import Counter
from ottosave import loadObarcMerged, parseTime, formatTime, loadIndex
from datetime import datetime
index = loadIndex()
counts = {}

for bid in index.keys():
    info = index[bid]
    time_s = datetime.fromtimestamp(info['arcts']).strftime('%Y%m%d')
    if info['ts'] == parseTime("2000-1-1 00:00:00"):
        type_ = 0 if info['c_len'] == 0 else 1
    else:
        type_ = 2
    counts[int(bid)] = (type_, time_s)

counts_by_bid = counts

def printColors(start, end):
    res = ""
    for bid in range(start, end):
        t = counts_by_bid.get(bid, (3, '_'))
        res += ('\033[38;5;196m█\033[0m',
                '\033[38;2;244;177;2m█\033[0m',
                '\033[38;2;65;205;82m█\033[0m',
                '\033[38;2;127;127;127m█\033[0m')[t[0]]
    print(res+"\033[0m")

def printColorsNoGhost(start, end):
    res = ""
    for bid in range(start, end):
        t = counts_by_bid.get(bid, (3, '_'))
        res += ('\033[38;5;196m██\033[0m',
                '\033[38;5;196m██\033[0m',
                '\033[38;2;65;205;82m██\033[0m',
                '\033[38;2;127;127;127m██\033[0m')[t[0]]
    print(res+"\033[0m")


def printHtml(start, end):
    items = []
    for bid in range(start, end):
        stat = counts_by_bid.get(bid, (3, 'u'))[0]
        type_map = {0:'d', 1:'g', 2:'n', 3:'u'}
        time_str = counts[bid][1][-2:] if bid in counts else 'xx'
        items.append(f'{{bid:{bid},ty:\'{type_map[stat]}\',t:\'{time_str}\'}}')
    return f'[{",".join(items)}]'


def main1(a,b):
    for row in range(a,b):
        start = row * 200 + 1
        end = start + 200
        print(f"{start:05}~{end-1:05}:",end="")
        printColors(start, end)

def main2(a,b):
    for row in range(a,b):
        start = row * 100 + 1
        end = start + 100
        print(f"{start:05}~{end-1:05}:",end="")
        printColorsNoGhost(start, end)


if __name__ == '__main__':
    print()
    #with open("D:/print.txt","w") as fp:
    #    fp.write(printHtml(1,10001))
    main1(0,240)
