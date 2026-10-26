#!/bin/bash
cd "$(dirname "$0")"

if command -v uv >/dev/null 2>&1; then
    if [ ! -d ".venv" ]; then
        echo "Configurando entorno virtual e instalando dependencias con uv..."
        uv sync
    fi
    uv run python main.py "$@"
else
    if [ ! -d ".venv" ]; then
        echo "Creando entorno virtual..."
        python3 -m venv .venv
    fi

    source .venv/bin/activate

    if ! python -c "import rich, halo, simple_term_menu" >/dev/null 2>&1; then
        echo "Instalando dependencias..."
        pip install -r requirements.txt
    fi

    python main.py "$@"
fi

