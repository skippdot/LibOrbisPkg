"""GP4 for an EU (CUSA07904) + Russian-language hybrid of MW2 Campaign Remastered.

Usage: make_hybrid_mw2cr.py <eu_extract_dir> <ru_part_dir> <out_dir>

- Everything from the EU extraction (keeps the airport / "No Russian" mission and the EU eboot).
- Adds russian/ and russian_partial/ plus chunks.rus / chunks.rup from the RU extraction.
- The RU build has no airport-localized files; English ones are used under the Russian names,
  so that mission falls back to English.
- chunks.<lang> map levels to PlayGo chunk ids of the original multi-chunk package. The rebuilt
  package has a single chunk (0), so every level is pointed at chunk 0.
Confirmed launching on a retail PS4 (FW 12.00, GoldHEN) uncompressed, 2026-10-07.
"""
import os
import sys
import xml.etree.ElementTree as ET

MISSING_STEMS = ["airport.ff", "patch_airport.ff", "soundfile63.pak"]
LANGS = {"russian": "rus", "russian_partial": "rup"}


def main(eu, ru, out):
    tree = ET.parse(os.path.join(eu, "Project.gp4"))
    root = tree.getroot()
    files_el = root.find("files")
    files = {f.get("targ_path"): os.path.join(eu, f.get("orig_path")) for f in files_el.iter("file")}

    for d in LANGS:
        for name in sorted(os.listdir(os.path.join(ru, d))):
            if not name.startswith("._"):
                files[f"{d}/{name}"] = os.path.join(ru, d, name)
    for d, pre in LANGS.items():
        for stem in MISSING_STEMS:
            files.setdefault(f"{d}/{pre}_{stem}", os.path.join(eu, "english", f"eng_{stem}"))

    extra = os.path.join(out, "extra")
    os.makedirs(extra, exist_ok=True)
    chunk_sources = {n: os.path.join(eu, n) for n in os.listdir(eu) if n.startswith("chunks.")}
    chunk_sources.update({n: os.path.join(ru, n) for n in ("chunks.rus", "chunks.rup")})
    for name, src in sorted(chunk_sources.items()):
        lines = [l.rstrip("\r\n") for l in open(src, encoding="ascii") if l.strip()]
        dst = os.path.join(extra, name)
        with open(dst, "w", encoding="ascii", newline="\n") as f:
            f.write("\n".join(l.split("\t")[0] + "\t0" for l in lines) + "\n")
        files[name] = dst

    missing = [p for p in files.values() if not os.path.isfile(p)]
    if missing:
        sys.exit(f"missing source files: {missing[:5]}")
    lower = {}
    for t in files:
        if t.lower() in lower:
            sys.exit(f"case-only duplicate: {t} / {lower[t.lower()]}")
        lower[t.lower()] = t

    for f in list(files_el):
        files_el.remove(f)
    for t in sorted(files, key=lambda t: (not t.startswith("sce_sys/"), t)):
        el = ET.SubElement(files_el, "file")
        el.set("targ_path", t)
        el.set("orig_path", files[t])

    rootdir = root.find("rootdir")
    nodes = {"": rootdir}

    def index(el, prefix):
        for d in el.findall("dir"):
            key = prefix + d.get("targ_name")
            nodes[key] = d
            index(d, key + "/")

    index(rootdir, "")
    for t in sorted(files):
        parts = t.split("/")[:-1]
        for i in range(len(parts)):
            key = "/".join(parts[: i + 1])
            if key not in nodes:
                el = ET.SubElement(nodes["/".join(parts[:i])], "dir")
                el.set("targ_name", parts[i])
                nodes[key] = el

    ET.indent(tree)
    tree.write(os.path.join(out, "Project.gp4"), encoding="utf-8", xml_declaration=True)
    print(f"files={len(files)}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
