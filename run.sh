#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

if ! python -c "import rich, halo, simple_term_menu" >/dev/null 2>&1; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

python main.py "$@"
