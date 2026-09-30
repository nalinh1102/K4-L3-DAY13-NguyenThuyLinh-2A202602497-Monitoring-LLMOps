#!/usr/bin/env bash
# Open this project in its Python virtual environment (Git Bash).
# Usage: source scripts/enter-venv.sh

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "Run this script with: source scripts/enter-venv.sh" >&2
  exit 1
fi

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
venv_activate="$project_root/.venv/Scripts/activate"

if [[ ! -f "$venv_activate" ]]; then
  echo "Virtual environment was not found: $venv_activate" >&2
  echo "Create it first with: python -m venv .venv" >&2
  return 1
fi

cd -- "$project_root" || return 1
source "$venv_activate"

echo "Project: $PWD"
echo "Python: $(python --version)"
