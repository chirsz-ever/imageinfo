#!/usr/bin/env python3

import argparse
import struct
from iccinfo import decode_tags, parse_desc

class Segment:
    def __init__(self, marker, offset, length):
        self.marker = marker
        self.offset = offset
        self.length = length


segment_defs = {
    "SOI": 0xD8, # 文件头
    "APP0": 0xE0, # 应用程序数据
    "APP1": 0xE1,
    # "APPn": 0xEn,
    "DQT": 0xDB,  # 定义量化表
    "SOF0": 0xC0,  # 图像基本信息
    "SOF2": 0xC2,  # 同上
    "DHT": 0xC4,  # 定义 Huffman 表（霍夫曼表）
    "DRI": 0xDD,  # 定义重新开始间隔
    "SOS": 0xDA,  # 扫描行开始
    "COM": 0xFE,  # 注释
    "EOI": 0xD9,  # 文件尾
}

def is_rst(marker):
    return 0xD0 <= marker <= 0xD7

def segment_name(marker):
    if is_rst(marker):
        return f"RST{marker & 0x0F:X}"
    if 0xE0 <= marker <= 0xEF:
        return f"APP{marker & 0x0F:X}"
    for name, m in segment_defs.items():
        if m == marker:
            return name
    raise Exception(f"unknown marker {marker:02X}")

zero_size_markers = list(map(segment_defs.get, ["SOI", "EOI", "SOS"]))

def is_zero_size(marker):
    return zero_size_markers.count(marker) > 0 or is_rst(marker)


def decode_segments(data):
    offset = 1
    assert data[0] == 0xFF
    while offset < len(data):
        while data[offset] == 0xFF and offset < len(data):
            offset += 1
        if offset >= len(data):
            break
        marker = struct.unpack(">B", data[offset : offset + 1])[0]
        if is_zero_size(marker):
            zero_size = True
            seg_size = 0
        else:
            zero_size = False
            seg_size = struct.unpack(">H", data[offset + 1 : offset + 3])[0]
        yield Segment(marker, offset - 1, seg_size)

        if zero_size:
            offset += 1
        else:
            offset += 1 + seg_size

        if marker == 0xDA or is_rst(marker): # SOS
            while offset < len(data) - 1:
                if data[offset] == 0xFF and data[offset + 1] != 0x00:
                    break
                offset += 1
        else:
            if offset < len(data) and data[offset] != 0xFF:
                raise Exception(f"offset {offset:04X} is not 0xFF")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="PNG file to read")
    parser.add_argument("--save-icc", help="save icc profile", action="store_true")
    args = parser.parse_args()
    with open(args.file, "rb") as f:
        data = f.read()
    if list(data[:3]) != [0xFF, 0xD8, 0xFF]:
        print(f"Not a JPEG file, HEADER is {data[:3]}")
        return
    for seg in decode_segments(data):
        if is_rst(seg.marker):
            continue
        print(
            f"seg marker: {seg.marker:02X} ({segment_name(seg.marker):<4}), offset: {seg.offset:04X}, length: {seg.length:04X}"
        )
        if seg.marker == 0xDD: # DRI
            dri = struct.unpack(">H", data[seg.offset+3:seg.offset+5])[0]
            print(f"  restart interval: {dri}")
        elif seg.marker == 0xE2: # APP2
            # https://dev.exiv2.org/projects/exiv2/wiki/The_Metadata_in_JPEG_files
            icc_info = data[seg.offset+4:seg.offset+4+14]
            icc_name, icc_chunk_count, icc_total_chunks = struct.unpack(">12sBB", icc_info)
            print(f"  ICC Identifier: {icc_name.decode()}")
            print(f"  ICC Chunk Count: {icc_chunk_count}")
            print(f"  ICC Total Chunks: {icc_total_chunks}")
            icc_profile_data = data[seg.offset+4+14:seg.offset+2+seg.length]
            if args.save_icc:
                icc_filename = f"{args.file}.icc"
                print(f"  Saving ICC profile to {icc_filename}")
                with open(icc_filename, "wb") as f:
                    f.write()
            icc_tags = decode_tags(icc_profile_data)
            for tag in icc_tags:
                if tag.sig == b'desc':
                    desc_data = icc_profile_data[tag.offset:tag.offset+tag.size]
                    desc_result = parse_desc(desc_data)
                    print(f' {desc_result.name}: {desc_result.desc}')

if __name__ == "__main__":
    main()
