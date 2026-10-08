#!/bin/bash
# Build and verify a pkg from a GP4 project, optionally PFSC-compressed, keeping peak disk use low.
# Usage: [COMPRESS=0] build_pkg.sh <project_dir_with_Project.gp4> <work_dir> <output.pkg>
# Intermediates (inner image, PFSC copy, verification extract) live in <work_dir> and are removed
# by this script as soon as they have been checked.
set -euo pipefail

PROJ=$(cd "$1" && pwd); WORK=$2; OUT=$3
TOOLS=$(cd "$(dirname "$0")" && pwd)
T=${PKGTOOL:-$TOOLS/../../PkgTool.Core/bin/Release/net8.0/PkgTool.Core}
export DOTNET_ROOT=${DOTNET_ROOT:-$HOME/.dotnet}
COMPRESS=${COMPRESS:-1}
mkdir -p "$WORK/out"
rm -f "$WORK"/out/*.pkg
rm -rf "$WORK/verify"

PFSC_ARGS=()
if [ "$COMPRESS" = 1 ]; then
  echo "== inner image"
  (cd "$PROJ" && "$T" pfs_buildinner Project.gp4 "$WORK/inner.dat" >/dev/null)
  echo "== PFSC"
  python3 "$TOOLS/pfsc_compress.py" "$WORK/inner.dat" "$WORK/inner.pfsc" | tail -1
  # Independent decode (zlib + adler32) of every block against the raw image, before building.
  python3 "$TOOLS/verify_merged.py" "$WORK" "$WORK/inner.pfsc"
  rm -f "$WORK/inner.dat"
  PFSC_ARGS=(--pfsc "$WORK/inner.pfsc")
fi

echo "== pkg build"
(cd "$PROJ" && "$T" pkg_build ${PFSC_ARGS[@]+"${PFSC_ARGS[@]}"} Project.gp4 "$WORK/out" | tail -1)
rm -f "$WORK/inner.pfsc"
BUILT=$(ls "$WORK"/out/*.pkg)

echo "== verify"
errors=$("$T" pkg_validate "$BUILT" 2>&1 | grep -c ERROR || true)
[ "$errors" = 0 ] || { echo "pkg_validate: $errors errors"; exit 1; }
# Full read-back through the package (decrypt, decompress) and byte compare with the sources.
"$T" pkg_makegp4 "$BUILT" "$WORK/verify" >/dev/null
python3 "$TOOLS/verify_merged.py" "$WORK" --project "$PROJ"
head -c 4 "$WORK/verify/sce_sys/nptitle.dat" 2>/dev/null | grep -q NPTD || [ ! -f "$WORK/verify/sce_sys/nptitle.dat" ] \
  || { echo "nptitle.dat is not plaintext"; exit 1; }
rm -rf "$WORK/verify"

mv "$BUILT" "$OUT"
echo "OK -> $OUT ($(stat -f %z "$OUT") bytes)"
