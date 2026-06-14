#!/bin/bash
# Compile translation files (.po) to standard binary format (.mo)

set -e

# Get the root directory of the project
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "Compiling locales..."

mkdir -p pyingestion/locale/en/LC_MESSAGES
mkdir -p pyingestion/locale/pt/LC_MESSAGES

msgfmt -o pyingestion/locale/en/LC_MESSAGES/messages.mo pyingestion/locale/en/messages.po
msgfmt -o pyingestion/locale/pt/LC_MESSAGES/messages.mo pyingestion/locale/pt/messages.po

echo "Locales compiled successfully!"
