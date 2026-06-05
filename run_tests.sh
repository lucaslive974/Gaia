#!/bin/bash
# run_tests.sh
# Script para execução simplificada da suíte de testes unitários no Gaia.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

if [ -f "./.venv/bin/python" ]; then
    PYTHON_BIN="./.venv/bin/python"
elif [ -f "./.venv/bin/python3" ]; then
    PYTHON_BIN="./.venv/bin/python3"
else
    PYTHON_BIN="python3"
    echo "⚠️  Aviso: Ambiente virtual (.venv) não localizado na raiz. Utilizando o python3 global."
fi

echo "🧪 Executando suíte de testes unitários (Gaia)..."
$PYTHON_BIN -m unittest discover -s tests -v
