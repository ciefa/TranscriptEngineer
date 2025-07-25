#!/bin/bash
# Voice to Docs runner script
# Usage: ./run.sh [options]

cd "$(dirname "$0")"
./venv/bin/python voice_to_docs.py "$@"