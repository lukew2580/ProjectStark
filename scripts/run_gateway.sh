#!/bin/bash
# Hardwareless AI — Cognitive Gateway Launcher
# Mobile-Aware version (Phase 8)

export PYTHONPATH="$(pwd)"

case "$1" in
    --mobile)
        echo "--- [MOBILE STABLE MODE] ---"
        echo "Disabling file-watcher for emulated mobile terminals (iSH/Termux)..."
        RELOAD_FLAG=""
        ;;
    *)
        RELOAD_FLAG="--reload"
        ;;
esac

echo "--- Phase 1: Cognitive Bootstrap ---"
python3 scripts/bootstrap_kb.py

echo "--- Phase 2: Swarm Ignition ---"
export BOOTSTRAP_COGNITION=1

# Local IP Discovery for Mobile Access
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I | awk '{print $1}')
echo "--- [NETWORK INFO] ---"
echo "Gateway Access: http://localhost:8000"
if [ ! -z "$LOCAL_IP" ]; then
    echo "Mobile Access:  http://$LOCAL_IP:8000"
fi

python3 -m uvicorn gateway.app:app --host 0.0.0.0 --port 8000 $RELOAD_FLAG
