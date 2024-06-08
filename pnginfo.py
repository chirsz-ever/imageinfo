#!/usr/bin/env python3

import argparse
import struct
import zlib

from iccinfo import decode_tags, parse_desc

class Chunk:
    def __init__(self, type, data, offset, crc_right):
        self.type = type
        self.data = data
        self.offset = offset
        self.crc_right = crc_right

def decode_chunks(data):
    offset = 8
    while offset < len(data):
        length, type = struct.unpack(">I4s", data[offset:offset+8])
        chunk_data = data[offset+8:offset+8+length]
        crc_saved, = struct.unpack(">I", data[offset+length+8:offset+length+12])
        crc_calc = zlib.crc32(data[offset+4:offset+length+8])
        if crc_saved != crc_calc:
            print(f'{crc_saved=}, {crc_calc=}')
        yield Chunk(type, chunk_data, offset, crc_saved == crc_calc)
        offset += 8 + length + 4

def print_iCCP_info(data: bytes, save_icc, file):
    offset_nul = data.find(b'\0')
    profile_name = data[:offset_nul].decode('latin-1')
    print(f"  Profile Name: {profile_name}")
    compressed_profile = data[offset_nul+2:]
    print(f"  Compressed Profile: {len(compressed_profile)} bytes")
    # print(f'  {compressed_profile[:10]}')
    profile = zlib.decompress(compressed_profile)
    profile_save_name = f"{file}.icc"
    if save_icc:
        with open(profile_save_name, "wb") as f:
            f.write(profile)
        print(f"  Profile: {len(profile)} bytes, save to {profile_save_name}")
    else:
        print(f"  Profile: {len(profile)} bytes")
    icc_tags = decode_tags(profile)
    for tag in icc_tags:
        if tag.sig == b'desc':
            desc_data = profile[tag.offset:tag.offset+tag.size]
            desc_result = parse_desc(desc_data)
            print(f'  {desc_result.name}: {desc_result.desc}')

def parse_color_type(color_type):
    if color_type == 0:
        return "Grayscale"
    elif color_type == 2:
        return "Truecolor"
    elif color_type == 3:
        return "Indexed-color"
    elif color_type == 4:
        return "Gray+Alpha"
    elif color_type == 6:
        return "Truecolor+Alpha"
    else:
        return f"Unknown: {color_type}"

def print_IHDR_info(data: bytes):
    width, height, bit_depth, color_type, compression_method, filter_method, interlace_method = struct.unpack(">IIBBBBB", data)
    print(f"  Width: {width}")
    print(f"  Height: {height}")
    print(f"  Bit Depth: {bit_depth}")
    print(f"  Color Type: {parse_color_type(color_type)}")
    if compression_method != 0 or filter_method != 0 or interlace_method != 0:
        print(f"  Compression Method: {compression_method}")
        print(f"  Filter Method: {filter_method}")
        print(f"  Interlace Method: {interlace_method}")

def print_zTXt_info(data: bytes):
    offset_nul = data.find(b'\0')
    keywords = data[:offset_nul].decode('latin-1')
    compression_method = data[offset_nul+1]
    assert compression_method == 0, compression_method
    compression_text = data[offset_nul+2:]
    text_bytes = zlib.decompress(compression_text)
    if len(text_bytes) < 40:
        content = text_bytes.decode()
    else:
        content = f"({len(text_bytes)} bytes)"
    print(f"  Keywords: {keywords}")
    print(f"  Content: {content}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="PNG file to read")
    parser.add_argument("--save-icc", help="save icc profile", action='store_true')
    args = parser.parse_args()
    with open(args.file, "rb") as f:
        data = f.read()
    if list(data[:4]) != [0x89, 0x50, 0x4E, 0x47]:
        print(f"Not a PNG file, HEADER is {data[:4]}")
        return
    for chunk in decode_chunks(data):
        if chunk.type == b"IDAT":
            continue
        if chunk.crc_right:
            print(f'{chunk.type}, offset={chunk.offset}')
        else:
            print(f'{chunk.type}, offset={chunk.offset}, CRC32 check failed')
            continue
        if chunk.type == b"iCCP":
            print_iCCP_info(chunk.data, args.save_icc, args.file)
        elif chunk.type == b"IHDR":
            print_IHDR_info(chunk.data)
        elif chunk.type == b"gAMA":
            gamma, = struct.unpack(">I", chunk.data)
            print(f"  Gamma: {gamma} ({gamma/100000})")
        elif chunk.type == b'zTXt':
            print_zTXt_info(chunk.data)

if __name__ == "__main__":
    main()
