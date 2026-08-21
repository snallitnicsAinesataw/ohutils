import glob, re
# from collections import Counter
from ohutils import parseTime, formatTime
from ohutils.arc import loadBlogIndex
from datetime import datetime
index = loadBlogIndex()
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
        # type_map = {0:'d', 1:'g', 2:'n', 3:'u'}
        type_map = {0: 'd', 1: 'd', 2: 'n', 3: 'u'}  # for public
        time_str = counts[bid][1][-4:] if bid in counts else 'xxxx'
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
    A = """<!DOCTYPE HTML>
<html>
<head>
<title>OTTOVisual</title>
<meta charset="utf-8">
<style>

:root {
    --bg-wh: 12px;
    --blk-wh: 12px;
 }/*
.time-20260504{background-color: #a8d8ff;}
.time-20260505{background-color: #d9b8ff;}
.time-20260510{background-color: #ffb7d2;}
.time-20260511{background-color: #c0e0d9;}
.time-20260513{background-color: #ffe0a3;}
.time-20260514{background-color: #b3e2fa;}
.time-20260515{background-color: #f5c6e0;}
.time-20260516{background-color: #c9e4de;}
.time-20260516{background-color: #d9f4ee;}
.time-20260517{background-color: #e0d3ff;}
.time-20260518{background-color: #ffccbc;}
.time-20260520{background-color: #fdf5e6;}
.time-20260521{background-color: #e5f0fc;}
.time-20260522{background-color: #f0f5f5;}
.time-20260524{background-color: #fde4d3;}
.time-20260529{background-color: #eef0e3;}
.time-20260530{background-color: #ddf4f0;}
.time-202605xx{background-color: #606060;}
*/
.timeline {display: flex; flex-wrap: wrap; width: calc(var(--bg-wh)*var(--row-count) + 20px); margin: 0 auto; margin-top: 100px;}
.timeline-row { display: flex; align-items: center; height: var(--bg-wh);}
.item {width: var(--bg-wh); height: var(--bg-wh); display: flex; align-items: center; justify-content: center; flex-shrink: 0;}
.block {width: var(--blk-wh); height: var(--blk-wh); cursor: pointer;}
.block:hover::after {content: attr(data-info); position: absolute; background: #000; color: #fff; font-size: 12px; padding: 2px 4px; white-space: nowrap; transform: translateY(-100%);}
.n{ background-color: #65cd52;}
.d{ background-color: #e3342f;}
.g{ background-color: #f4ed02;}
.u{background-color: #7f7f7f;}
.row-idx {display: inline-block; width: 20px;font-size: 12px;text-align: right;padding-right: 6px;color: #aaa;flex-shrink: 0;}
.timeline-row.header {margin-bottom: 4px;}
.col-header {width: var(--bg-wh);text-align: center;font-size: 10px;color: #888;flex-shrink: 0;}
</style>
</head>
<body>
<div class="timeline" id="timeline"></div>
</body>
<script>
const bids = """
    B = """;
</script>
<script>
const container = document.getElementById('timeline');
const headerRow = document.createElement('div');
headerRow.className = 'timeline-row header';
const emptyHeader = document.createElement('span');
emptyHeader.className = 'row-idx';
emptyHeader.innerText = '';
headerRow.appendChild(emptyHeader);
for (let i = 1; i <= 100; i++) {
    const colHeader = document.createElement('div');
    colHeader.className = 'col-header';
    colHeader.innerText = i;
    headerRow.appendChild(colHeader);
}
container.appendChild(headerRow);

for (let i = 0; i < bids.length; i += 100) {
    const row = document.createElement('div');
    row.className = 'timeline-row';
    const rowIdx = document.createElement('span');
    rowIdx.className = 'row-idx';
    rowIdx.innerText = `${Math.floor(i / 100)}`;
    row.appendChild(rowIdx);
    for (let j = 0; j < 100; j++) {
        const bidData = bids[i + j];
        if (!bidData) break;
        const item = document.createElement('div');
        //item.className = `item time-2026${bidData.t}`;
        //item.className = 'item';
        const block = document.createElement('div');
        block.className = `block ${bidData.ty}`;
        block.dataset.info = `${bidData.bid} @ 2026-${bidData.t.slice(0,2)}-${bidData.t.slice(2)}`;
        item.appendChild(block);
        row.appendChild(item);
    }
    container.appendChild(row);
}
</script>
</html>"""
    with open("visual.html","w") as fp:
        fp.write(A+printHtml(1,50001)+B)
    #main2(0,500)
