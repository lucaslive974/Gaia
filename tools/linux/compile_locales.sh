#!/bin/bash
# Compile translation files (.po) to standard binary format (.mo)

set -e

# Get the root directory of the project
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "Compiling locales..."

mkdir -p locale/en/LC_MESSAGES
mkdir -p locale/pt/LC_MESSAGES

msgfmt -o locale/en/LC_MESSAGES/messages.mo locale/en/messages.po
msgfmt -o locale/pt/LC_MESSAGES/messages.mo locale/pt/messages.po

echo "Locales compiled successfully!"
