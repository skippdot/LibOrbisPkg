#!/bin/bash
# Merge a PS4 fake base pkg + patch pkg into one compressed (PFSC) app pkg.
# Usage: merge_pkg.sh <base.pkg> <patch.pkg> <work_dir> <output.pkg>
# Needs the patched PkgTool.Core (stream write, PFSC read fix, --pfsc option) in $PKGTOOL.
set -euo pipefail

BASE_PKG=$1; PATCH_PKG=$2; WORK=$3; OUT=$4
TOOLS=$(cd "$(dirname "$0")" && pwd)
T=${PKGTOOL:-$TOOLS/../../PkgTool.Core/bin/Release/net8.0/PkgTool.Core}
export DOTNET_ROOT=${DOTNET_ROOT:-$HOME/.dotnet}

mkdir -p "$WORK"
echo "== extract"
[ -f "$WORK/base/Project.gp4" ] || "$T" pkg_makegp4 "$BASE_PKG" "$WORK/base" >/dev/null
[ -f "$WORK/patch/Project.gp4" ] || "$T" pkg_makegp4 "$PATCH_PKG" "$WORK/patch" >/dev/null

echo "== merge gp4"
cp "$TOOLS/make_merged_gp4.py" "$WORK/"
python3 "$WORK/make_merged_gp4.py" "$T"

echo "== inner image + PFSC"
(cd "$WORK/merged" && "$T" pfs_buildinner Project.gp4 "$WORK/inner.dat" >/dev/null)
python3 "$TOOLS/pfsc_compress.py" "$WORK/inner.dat" "$WORK/inner.pfsc" | tail -1

echo "== pkg build"
mkdir -p "$WORK/out"
rm -f "$WORK"/out/*.pkg
(cd "$WORK/merged" && "$T" pkg_build --pfsc "$WORK/inner.pfsc" Project.gp4 "$WORK/out" | tail -1)
BUILT=$(ls "$WORK"/out/*.pkg)

echo "== verify"
errors=$("$T" pkg_validate "$BUILT" 2>&1 | grep -c ERROR || true)
[ "$errors" = 0 ] || { echo "pkg_validate: $errors errors"; exit 1; }
rm -rf "$WORK/verify" "$WORK/verify.pfsc"
"$T" pkg_extractinnerpfs --compressed --passcode 00000000000000000000000000000000 "$BUILT" "$WORK/verify.pfsc"
python3 "$TOOLS/verify_merged.py" "$WORK" "$WORK/verify.pfsc"
"$T" pkg_makegp4 "$BUILT" "$WORK/verify" >/dev/null
python3 "$TOOLS/verify_merged.py" "$WORK"

mv "$BUILT" "$OUT"
echo "OK -> $OUT ($(stat -f %z "$OUT") bytes)"
