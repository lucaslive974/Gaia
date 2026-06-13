#!/bin/bash
# Compile translation files (.po) to standard binary format (.mo)

set -e

# Get the root directory of the project
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "Compiling locales..."

mkdir -p pydocstructurer/locale/en/LC_MESSAGES
mkdir -p pydocstructurer/locale/pt/LC_MESSAGES

msgfmt -o pydocstructurer/locale/en/LC_MESSAGES/messages.mo pydocstructurer/locale/en/messages.po
msgfmt -o pydocstructurer/locale/pt/LC_MESSAGES/messages.mo pydocstructurer/locale/pt/messages.po

echo "Locales compiled successfully!"
