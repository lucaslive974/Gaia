#!/bin/bash
# Compile translation files (.po) to standard binary format (.mo)

set -e

# Get the root directory of the project
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "Compiling locales..."

mkdir -p pydocstruct/locale/en/LC_MESSAGES
mkdir -p pydocstruct/locale/pt/LC_MESSAGES

msgfmt -o pydocstruct/locale/en/LC_MESSAGES/messages.mo pydocstruct/locale/en/messages.po
msgfmt -o pydocstruct/locale/pt/LC_MESSAGES/messages.mo pydocstruct/locale/pt/messages.po

echo "Locales compiled successfully!"
