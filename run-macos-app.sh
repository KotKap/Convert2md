#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  cat <<EOF
Usage: $0 <app-bundle-path> <command> [args...]

Example:
  $0 dist/Convert2MDs.app convert '/path/to/document.docx'

This script launches the bundled app executable directly, passing arguments to it.
EOF
  exit 1
fi

APP_BUNDLE="$1"
shift

if [[ ! -d "$APP_BUNDLE" ]]; then
  echo "Error: App bundle not found: $APP_BUNDLE" >&2
  exit 1
fi

EXECUTABLE=$(find "$APP_BUNDLE/Contents/MacOS" -maxdepth 1 -type f | head -n 1)

if [[ -z "$EXECUTABLE" ]]; then
  echo "Error: No executable found in $APP_BUNDLE/Contents/MacOS" >&2
  exit 1
fi

exec "$EXECUTABLE" "$@"
