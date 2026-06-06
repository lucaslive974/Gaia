#!/bin/bash
# Compile translation files (.po) to standard binary format (.mo)

set -e

# Get the root directory of the project
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "Compiling locales..."

mkdir -p gaia/locale/en/LC_MESSAGES
mkdir -p gaia/locale/pt/LC_MESSAGES

msgfmt -o gaia/locale/en/LC_MESSAGES/messages.mo gaia/locale/en/messages.po
msgfmt -o gaia/locale/pt/LC_MESSAGES/messages.mo gaia/locale/pt/messages.po

echo "Locales compiled successfully!"
