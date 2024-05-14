#!/usr/bin/env python3

import argparse
import struct

class Tag:
    def __init__(self, sig, index, offset, size):
        self.sig = sig
        self.index = index
        self.offset = offset
        self.size = size

def decode_tags(data):
    offset = 128
    tag_count = struct.unpack(">I", data[offset:offset+4])[0]
    # print(f"{tag_count=}")
    offset += 4
    for i in range(tag_count):
        sig, tag_offset, size = struct.unpack(">4sII", data[offset:offset+12])
        yield Tag(sig, i, tag_offset, size)
        offset += 12

class DescriptionTagParseResult:
    def __init__(self, name, desc) -> None:
        self.name = name
        self.desc = desc

def parse_desc(data):
    name = data[:4].decode()
    # 6.5.17 textDescriptionType
    if data[:4] == b'desc':
        desc_len = struct.unpack(">I", data[8:12])[0]
        ascii_desc_str = data[12:12+desc_len].decode("ascii")
        # offset = 12 + desc_len
        # i10n_code = data[offset:offset+4]
        # unicode_len = struct.unpack(">I", data[offset+4:offset+8])[0]
        # unicode_desc_str = data[offset+8:offset+8+unicode_len].decode("utf-16")
        # offset += 8 + unicode_len
        # mac_lang_code = data[offset:offset+2]
        # offset += 2
        # mac_len = struct.unpack(">B", data[offset:offset+1])[0]
        # offset += 1
        # mac_desc_str = data[offset:].decode("mac-roman")
        # print(f"{i10n_code=}, {mac_lang_code=}, {mac_len=}")
        # print(f"{ascii_desc_str=}, {unicode_desc_str=}, {mac_desc_str=}")
        return DescriptionTagParseResult(name, ascii_desc_str)
    elif data[:4] == b'mluc':
        rec_count, rec_size = struct.unpack(">II", data[8:16])
        assert rec_size == 12, rec_size
        desc_str = ''
        for i in range(rec_count):
            record_data = data[16+12*i:16+12*(i+1)]
            lang, str_len, str_offset = struct.unpack('>4sII', record_data)
            utf16be_str = data[str_offset:str_offset+str_len].decode("utf-16be")
            lang_code = lang[:2].decode() + "-" + lang[2:].decode()
            desc_str += f'"{lang_code}": "{utf16be_str}", '
        return DescriptionTagParseResult(name, desc_str)

    return DescriptionTagParseResult(name, "**Unknown**")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="PNG file to read")
    args = parser.parse_args()
    with open(args.file, "rb") as f:
        data = f.read()
    for tag in decode_tags(data):
        print(f"tag {tag.index:2}: {tag.sig}, offset: {tag.offset}, size: {tag.size}")
        if tag.sig == b"desc":
            desc_data = data[tag.offset:tag.offset+tag.size]
            desc_result = parse_desc(desc_data)
            print(f' {desc_result.name}: {desc_result.desc}')

if __name__ == "__main__":
    main()
