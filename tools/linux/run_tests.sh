#!/bin/bash
# run_tests.sh
# Script para execução da suíte de testes unitários no Gaia.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$DIR/../.." && pwd )"
cd "$PROJECT_ROOT"

if [ -f "./.venv/bin/python" ]; then
    PYTHON_BIN="./.venv/bin/python"
elif [ -f "./.venv/bin/python3" ]; then
    PYTHON_BIN="./.venv/bin/python3"
else
    PYTHON_BIN="python3"
    echo "⚠️  Aviso: Ambiente virtual (.venv) não localizado na raiz. Utilizando o python3 global."
fi

if [ -f "./.venv/bin/pytest" ]; then
    TEST_BIN="./.venv/bin/pytest"
else
    TEST_BIN="$PYTHON_BIN -m pytest"
fi

echo "🧪 Executando suíte de testes unitários (Gaia)..."
$TEST_BIN -v
