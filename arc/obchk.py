from ..core.util import encrypt, decrypt, Comment, BlogEntry, genKey
from ..core.config import Config, getGlobalConfig
import zlib
import struct
from .obarc import _parseBlog
from typing import Union
import os
import time


class BlogChunk:
    def __init__(self, **kwargs):
        """无需实例化，应使用loadChunk()创建。"""
        self._fp = kwargs['filepath']
        self._cache = {}  # {bid:int -> BlogEntry}
        self._index = self._load_index()   # {bid:int -> offset:int}

    def _load_index(self):
        with open(self._fp, 'rb', encoding='utf-8') as f:
            ...

    def __getitem__(self, bid: int):
        ...

    def __len__(self):
        len(self._index)

    def __iter__(self):
        return iter(self._index.keys())

    def keys(self):
        return self._index.keys()

    def values(self):
        for bid in self._index:
            yield self[bid]

    def items(self):
        for bid in self._index:
            yield bid, self[bid]

    def get(self, bid: int, default=None):
        try:
            return self.__getitem__(bid)
        except KeyError:
            return default


def serializeBlog(bid: int, config: Config = None) -> bytes:
    """将指定bid的.obarc文件序列化。"""
    if config is None:
        config = getGlobalConfig()
    with open(os.path.join(config.savePath, config.fileName.format(bid=bid)), "rb") as fp:
        data = fp.read()

    new = data[5:24] + data[28:31] + data[32:-18]
    return new


def deserializeBlog(data: bytes) -> BlogEntry:
    """反序列化二进制数据。"""
    # 解析头部
    version = data[0]
    flags = data[1]
    tag_count = data[21]
    pub_ts = struct.unpack_from('<I', data, 3)[0]
    arc_ts = struct.unpack_from('<I', data, 7)[0]
    channel_id = struct.unpack_from('<H', data, 19)[0]

    # 数据区从第22字节开始
    blog_data = data[22:]
    blog, _ = _parseBlog(version, blog_data, flags, 0, channel_id, pub_ts, arc_ts, tag_count)
    return blog


def buildChunk(start: int, end: int, flags: Union[list[bool], list[int], int] = None, config: Config = None):
    """
    构建.obchk文件。
    标志:
    位0: 加密内容。
    """
    if config is None:
        config = getGlobalConfig()
    lookup_bias = config.lookupTableBias
    key, _ = genKey(config.password, config.salt)

    if lookup_bias < 32:
        raise ValueError("lookup table overlap with header")
    if flags is None:
        flags = [False] * 8
    is_list = isinstance(flags, list)
    if is_list and len(flags) > 8:
        raise ValueError("flags longer than 8")
    if is_list and all(isinstance(x, int) for x in flags) and any(x > 1 for x in flags):
        # invalid flags: list[int]
        raise ValueError("invalid int as bool")
    if is_list:
        flag_int = sum(bit << i for i, bit in enumerate(flags))
    else:
        flag_int = flags
        flags = [bool((flags >> i) & 1) for i in range(8)]
    if key is None and not flags[0]:
        raise ValueError("encryption without a key?")

    filename = os.path.join(config.chunkPath, config.blogChunkName.format(start=start, end=end, flag=flag_int))
    entries = []
    data_blocks = []
    data_bias = lookup_bias + (end - start + 1) * 8
    current_offset = data_bias

    for bid in range(start, end + 1):
        file = os.path.join(config.savePath, config.fileName.format(bid=bid))
        if not os.path.exists(file):
            entries.append(0)
            if config.verbose:
                print(f'[buildChunk]{config.colorYellow}File does not exist: {file}\033[0m')
            continue
        try:
            data = serializeBlog(bid)
            entries.append(current_offset)

            if flags[0]:
                data = encrypt(key, data)

            data_blocks.append(data)
            current_offset += len(data)
        except Exception as e:
            print(f"[buildChunk]Skip ob{bid}: {e}")
    entries.append(current_offset)  # 此处

    lookup_table = b''
    for offset in entries:
        lookup_table += struct.pack('<Q', offset + 8)
        # +8因为for循环末尾的一个额外QW (上方)

    with open(filename, "wb") as f:
        # 文件头（占位）
        f.write(b'OBCHK')
        f.write(struct.pack('<B', 1))  # 版本
        f.write(struct.pack('<B', flag_int))  # Flag
        f.write(struct.pack('<I', lookup_bias))
        f.write(struct.pack('<Q', 0))  # size 占位
        f.write(struct.pack('<I', 0))  # CRC32 占位
        f.write(struct.pack('<I', start))
        f.write(struct.pack('<I', end))
        f.write(b'\xA4')

        f.write(b'\x00' * (lookup_bias - 32))
        f.write(lookup_table)

        for data in data_blocks:
            f.write(data)

        # 打包时间
        pack_ts = int(time.time())
        f.write(struct.pack('<I', pack_ts))

        end_marker = bytes.fromhex("dc bd cc b2 e7 a2 d9 a4 f0 b1 b1 eb e6 e8 a8 dc bf b5 c4 a8 e8 dc b7")
        f.write(end_marker)

        # 回填大小和CRC32
        total_size = f.tell()

    with open(filename, "r+b") as f:
        f.seek(data_bias)
        all_data = f.read()[:-27]  # exclude pack_time & end marker
        crc32 = zlib.crc32(all_data) & 0xFFFFFFFF

        f.seek(0x0B)  # size偏移
        f.write(struct.pack('<Q', total_size))
        f.seek(0x13)  # CRC32偏移
        f.write(struct.pack('<I', crc32))
    print(f"[buildChunk]Chunk built: {filename}")


def loadChunk(filename: str, lazy: bool = False, config: Config = None) -> dict[int, BlogEntry]:
    """读取.obchk文件。
    若lazy=False，返回{bid: BlogEntry}。否则返回BlogChunk类，此类表现与dict一致。"""
    if config is None:
        config = getGlobalConfig()
    with open(filename, "rb") as f:
        header = f.read(32)
        flags = struct.unpack('<B', header[6:7])[0]
        start_bid = struct.unpack('<I', header[23:27])[0]
        end_bid = struct.unpack('<I', header[27:31])[0]
        lookup_bias = struct.unpack('<I', header[7:11])[0]

        if flags & 1:
            key, _ = genKey(config.password, config.salt)

        f.seek(lookup_bias)
        result = {}
        if lazy:
            ...
        else:
            for bid in range(start_bid, end_bid + 1):
                f.seek(lookup_bias + (bid - start_bid) * 8)
                try:
                    offset = struct.unpack('<Q', f.read(8))[0]
                except Exception as e:
                    if config.verbose:
                        print(f"[loadChunk]failed to read offset for bid={bid}: {e}\033[0m")
                    continue
                if offset == 0:
                    continue
                next_offset = struct.unpack('<Q', f.read(8))[0]
                data_len = next_offset - offset
                f.seek(offset)
                data = f.read(data_len)
                if flags & 1:
                    data = decrypt(key, data)
                blog = deserializeBlog(data)
                result[bid] = blog
    return result
