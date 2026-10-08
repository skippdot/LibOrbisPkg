#!/bin/bash
# Merge a PS4 fake base pkg + patch pkg into one compressed (PFSC) app pkg.
# Usage: [COMPRESS=0] merge_pkg.sh <base.pkg> <patch.pkg> <work_dir> <output.pkg>
# Needs the patched PkgTool.Core (stream write, PFSC read fix, --pfsc option) in $PKGTOOL.
set -euo pipefail

BASE_PKG=$1; PATCH_PKG=$2; WORK=$3; OUT=$4
TOOLS=$(cd "$(dirname "$0")" && pwd)
T=${PKGTOOL:-$TOOLS/../../PkgTool.Core/bin/Release/net8.0/PkgTool.Core}
export DOTNET_ROOT=${DOTNET_ROOT:-$HOME/.dotnet}

mkdir -p "$WORK"
echo "== extract"
[ -f "$WORK/base/Project.gp4" ] || "$T" pkg_makegp4 --passcode 00000000000000000000000000000000 "$BASE_PKG" "$WORK/base" >/dev/null
[ -f "$WORK/patch/Project.gp4" ] || "$T" pkg_makegp4 --passcode 00000000000000000000000000000000 "$PATCH_PKG" "$WORK/patch" >/dev/null

echo "== merge gp4"
cp "$TOOLS/make_merged_gp4.py" "$WORK/"
python3 "$WORK/make_merged_gp4.py" "$T"

"$TOOLS/build_pkg.sh" "$WORK/merged" "$WORK" "$OUT"
