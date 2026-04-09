# MHE SmartMonitor Architecture

## Overview

`MHE SmartMonitor` simulates a conveyor line with real-time monitoring, PLC-style state logic, SQL-backed event logging, and a SCADA-like dashboard.

## Core Flow

1. `simulator.py` generates conveyor metrics every second.
2. The simulator updates line state, faults, alarms, and sensor conditions.
3. `database.py` stores metric snapshots and event logs in `smartmonitor.db`.
4. `app.py` exposes the data through Flask API endpoints.
5. `templates/index.html` + `static/app.js` render the live dashboard.

## Main Components

- **Flask Web Layer**: serves the dashboard and APIs
- **Conveyor Simulator**: models throughput, speed, load, current, and faults
- **PLC-style Logic**: maps faults into `RUN`, `MONITOR`, `FAULT_LOCKOUT`, and `EMERGENCY_STOP`
- **SQLite Storage**: keeps historical data for analysis and reports
- **SCADA Dashboard**: displays live health, alerts, trends, KPI summaries, and PLC I/O

## API Endpoints

- `GET /health` — app health check
- `GET /api/status` — live system snapshot
- `GET /api/history` — recent metrics and events
- `GET /api/report` — KPI summary report
- `GET /api/report.csv` — downloadable maintenance report
- `POST /api/control` — operator actions like `start`, `stop`, `ack`, `jam`, `slowdown`, `overload`, `estop`, `clear`

## Interview Talking Points

- Demonstrates **material handling domain awareness** with conveyor and motor monitoring.
- Shows a **troubleshooting mindset** via jam, overload, slowdown, and emergency-stop logic.
- Mimics **industrial controls** using PLC-like states, permissives, and alarm acknowledgement.
- Combines **Python**, **SQL**, and a **web dashboard** into a complete diagnostics demo.
