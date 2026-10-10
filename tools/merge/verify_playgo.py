"""Check a pkg's PlayGo chunk hash table (playgo-chunk.sha) against the package data.

The console's installer (BGFT) verifies every 64 KiB chunk of the package against this table;
a mismatch fails the install with CE-36244-9 / 0x80990077. pkg_validate does not check it.

Usage: verify_playgo.py <pkg>   (needs PkgTool at ../../PkgTool.Core/bin/Release/net8.0/)
"""
import hashlib
import os
import subprocess
import sys
import tempfile

CHUNK = 0x10000
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "../../PkgTool.Core/bin/Release/net8.0/PkgTool.Core")


def entry_id(pkg, name):
    out = subprocess.run([TOOL, "pkg_listentries", pkg], capture_output=True, text=True,
                         env=dict(os.environ, DOTNET_ROOT=os.environ.get("DOTNET_ROOT", os.path.expanduser("~/.dotnet")))).stdout
    for line in out.splitlines():
        if line.strip().endswith(name):
            return line.split()[3], int(line.split()[0], 16)
    sys.exit(f"{name} entry not found")


def main(pkg):
    idx, _ = entry_id(pkg, "PLAYGO_CHUNK_SHA")
    with tempfile.NamedTemporaryFile() as t:
        subprocess.run([TOOL, "pkg_extractentry", pkg, idx, t.name], check=True, capture_output=True,
                       env=dict(os.environ, DOTNET_ROOT=os.environ.get("DOTNET_ROOT", os.path.expanduser("~/.dotnet"))))
        table = open(t.name, "rb").read()
    size = os.path.getsize(pkg)
    n = size // CHUNK
    bad, zero, checked = [], 0, 0
    with open(pkg, "rb") as f:
        for i in range(min(n, len(table) // 4)):
            want = table[i * 4: i * 4 + 4]
            data = f.read(CHUNK)
            if want == b"\0\0\0\0":
                zero += 1          # not covered (pkg header/body area)
                continue
            checked += 1
            if hashlib.sha256(data).digest()[:4] != want:
                bad.append(i)
    print(f"{os.path.basename(pkg)}: chunks={n} table={len(table)//4} checked={checked} "
          f"uncovered={zero} mismatches={len(bad)} first={bad[:5]}")
    sys.exit(1 if bad or len(table) // 4 < n else 0)


if __name__ == "__main__":
    main(sys.argv[1])
