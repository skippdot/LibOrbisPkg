# Merge a PS4 fake base pkg + patch pkg into one compressed app pkg

```
tools/merge/merge_pkg.sh <base.pkg> <patch.pkg> <work_dir> <output.pkg>
```

Steps: `pkg_makegp4` both → `make_merged_gp4.py` (patch overrides base, case-insensitively;
patch-only delta files dropped; `CATEGORY=gd`) → `pfs_buildinner` → `pfsc_compress.py`
(zlib level 6, 4 KiB window, as retail) → `pkg_build --pfsc` → `verify_merged.py`
(PFSC decoded independently with adler32 checks, and every file compared byte-for-byte).

Requires PkgTool from the `feature/pfsc-compression` branch (build `PkgTool.Core` in Release).
