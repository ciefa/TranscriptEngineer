#!/bin/bash
# Voice to Engineering Requirements runner script
# Usage: ./run.sh [options]
# Examples:
#   ./run.sh                           # Normal mode
#   ./run.sh --mode agile-pm           # Agile PM mode for GitHub issues
#   ./run.sh --mode agile-pm --github-repo owner/repo  # With GitHub integration

cd "$(dirname "$0")"

# Suppress ALSA/JACK audio warnings
export ALSA_PCM_CARD=default
export ALSA_PCM_DEVICE=0
export PULSE_RUNTIME_PATH="/tmp/pulse-socket"

# Run with stderr filtered to remove audio system warnings
./venv/bin/python voice_to_docs.py "$@" 2> >(grep -v -E "(ALSA|JACK|Cannot connect to server|pcm_|snd_|JackShmReadWritePtr|jack server)" >&2)