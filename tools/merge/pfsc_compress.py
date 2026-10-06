"""Compress a raw inner PFS image into a PFSC container, the way retail/fake PKGs do.

Format (matches PFSCReader in LibOrbisPkg and a reference fpkg byte-for-byte):
  0x00 'PFSC' | 0x04 int 0 | 0x08 int 2 | 0x0C int block size | 0x10 long block size
  0x18 long offset of block table (0x400) | 0x20 long data start | 0x28 long logical length
  0x400 table of (n+1) longs: absolute start of each block, last entry = end of data
Each 64 KiB block is stored raw (exactly 64 KiB) or as zlib, level 6, 4 KiB window.

Usage: pfsc_compress.py <inner_pfs.dat> <out.pfsc> [workers]
"""
import os
import struct
import sys
import zlib
from multiprocessing import Pool

BLOCK = 0x10000
TABLE_OFFSET = 0x400
# Reference images never keep a compressed block above ~60 KiB; stay below that.
MAX_COMPRESSED = 0xF000
BATCH = 256  # blocks per worker task (16 MiB)


def header_size(num_blocks):
    # Same layout rule as LibOrbisPkg's PFSCWriter.
    table = 8 + num_blocks * 8
    extra = ((table - 0xFC00) + 0xFFFF) // 0x10000
    return 0x10000 + (BLOCK * extra if extra > 0 else 0)


def compress_batch(args):
    path, first, count = args
    out = []
    with open(path, "rb") as f:
        f.seek(first * BLOCK)
        for _ in range(count):
            raw = f.read(BLOCK)
            raw += b"\0" * (BLOCK - len(raw))
            c = zlib.compressobj(6, zlib.DEFLATED, 12)
            packed = c.compress(raw) + c.flush()
            out.append(packed if len(packed) < MAX_COMPRESSED else raw)
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else os.cpu_count()
    size = os.path.getsize(src)
    n = (size + BLOCK - 1) // BLOCK
    hdr_size = header_size(n)

    offsets = [hdr_size]
    tasks = [(src, i, min(BATCH, n - i)) for i in range(0, n, BATCH)]
    with open(dst, "wb") as out, Pool(workers) as pool:
        out.write(b"\0" * hdr_size)
        done = 0
        for blocks in pool.imap(compress_batch, tasks):
            for b in blocks:
                out.write(b)
                offsets.append(offsets[-1] + len(b))
            done += len(blocks)
            if done % (BATCH * 64) < BATCH:
                print(f"  {done}/{n} blocks, ratio {(offsets[-1] - hdr_size) / (done * BLOCK):.3f}", flush=True)
        out.seek(0)
        out.write(b"PFSC")
        out.write(struct.pack("<iiiqqQq", 0, 2, BLOCK, BLOCK, TABLE_OFFSET, hdr_size, n * BLOCK))
        out.seek(TABLE_OFFSET)
        out.write(struct.pack(f"<{n + 1}q", *offsets))
    print(f"{src}: {size} -> {offsets[-1]} bytes ({offsets[-1] / size:.3f}), {n} blocks")


if __name__ == "__main__":
    main()
