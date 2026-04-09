# MHE SmartMonitor: Real-Time Conveyor Diagnostics System

A portfolio-ready SCADA-style demo for conveyor monitoring, fault detection, and maintenance reporting.

## Features

- Simulated conveyor, motor, and load behavior
- Real-time dashboard for system health, throughput, current, and temperature
- Fault scenarios: `jam`, `slowdown`, `overload`, and `emergency stop`
- SQLite logging for metrics and events
- PLC-style control state (`RUN`, `IDLE`, `MONITOR`, `FAULT_LOCKOUT`, `EMERGENCY_STOP`)
- PLC I/O snapshot with `start permissive`, `photoeye`, `drive ready`, and `safety circuit`
- Alarm acknowledgement flow for a more SCADA-like operator experience
- Exportable CSV maintenance report for recent metrics and alerts
- Operator controls to start/stop the conveyor and inject faults

## Project Structure

- `app.py` - Flask web app and API routes
- `simulator.py` - Conveyor simulation and PLC-style logic
- `database.py` - SQLite metric, event, and report generation helpers
- `templates/index.html` - Dashboard UI
- `static/style.css` - SCADA-like styling
- `static/app.js` - Real-time polling and chart rendering

## Run Locally

1. Create/select a Python environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the app:
   ```bash
   python app.py
   ```
4. Open `http://127.0.0.1:5000`

## Demo Controls

Use the dashboard buttons to:
- Start or stop the conveyor
- Inject a jam
- Simulate overload or slowdown
- Trigger an emergency stop
- Clear the current fault
- Export a CSV maintenance report from the dashboard header

The app writes logs into `smartmonitor.db` automatically.
