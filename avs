#!/bin/sh
# AdCamp Video System: runs the AVS launcher (tools/avs.py) on AVS's own Python.
D="$(cd "$(dirname "$0")" && pwd)"
[ -x "$D/runtime/base/bin/python" ] || { echo "AVS is not set up yet on this Mac. Run bootstrap.sh in the AVS folder first."; exit 1; }
exec "$D/runtime/base/bin/python" "$D/tools/avs.py" "$@"
