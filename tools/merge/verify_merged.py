"""Verify a merged pkg build.

verify_merged.py <work> [--project <dir>] -> files extracted to <work>/verify match the project's sources
                                          (default <work>/merged) byte-for-byte
verify_merged.py <work> <image.pfsc>   -> PFSC pulled back out of the pkg decompresses (zlib, adler32-checked)
                                          to exactly <work>/inner.dat
"""
import filecmp
import os
import struct
import sys
import xml.etree.ElementTree as ET
import zlib


def check_pfsc(work, pfsc):
    with open(pfsc, "rb") as f, open(os.path.join(work, "inner.dat"), "rb") as raw:
        assert f.read(4) == b"PFSC", "bad magic"
        _, _, bs, _, table, _, length = struct.unpack("<iiiqqQq", f.read(0x2C))
        n = length // bs
        f.seek(table)
        offs = struct.unpack(f"<{n + 1}q", f.read(8 * (n + 1)))
        bad = 0
        for i in range(n):
            f.seek(offs[i])
            b = f.read(offs[i + 1] - offs[i])
            plain = b if len(b) == bs else zlib.decompress(b)
            want = raw.read(bs)
            bad += plain != want + b"\0" * (bs - len(want))
    print(f"PFSC: {n} blocks, mismatches {bad}")
    sys.exit(1 if bad else 0)


def check_files(work, project=None):
    def files(gp4):
        return {f.get("targ_path"): f.get("orig_path") for f in ET.parse(gp4).getroot().iter("file")}

    proj = project or os.path.join(work, "merged")
    src = {t: (o if os.path.isabs(o) else os.path.join(proj, o))
           for t, o in files(os.path.join(proj, "Project.gp4")).items()}
    out = files(os.path.join(work, "verify", "Project.gp4"))
    missing, extra = set(src) - set(out), set(out) - set(src)
    bad = [t for t in src if t in out
           and not filecmp.cmp(src[t], os.path.join(work, "verify", out[t]), shallow=False)]
    print(f"files: {len(src)} src, {len(out)} in pkg, missing {sorted(missing)}, extra {sorted(extra)}, mismatches {bad}")
    sys.exit(1 if missing or extra or bad else 0)


if __name__ == "__main__":
    if len(sys.argv) > 3 and sys.argv[2] == "--project":
        check_files(sys.argv[1], sys.argv[3])
    elif len(sys.argv) > 2:
        check_pfsc(sys.argv[1], sys.argv[2])
    else:
        check_files(sys.argv[1])
