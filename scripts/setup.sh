#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install -r requirements.txt
python verify_handoff.py
python -m unittest test_regime_rotation test_inverse_switch test_er_switch test_secondary_portfolio test_standalone_sideways test_breakout_er_portfolio test_idx_costs
