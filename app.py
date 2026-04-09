from __future__ import annotations

import atexit
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from flask import Flask, Response, render_template, request

from database import DatabaseManager
from simulator import ConveyorSimulator

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "smartmonitor.db"

app = Flask(__name__)
database = DatabaseManager(DB_PATH)
simulator = ConveyorSimulator(database)
simulator.start()
atexit.register(simulator.shutdown)


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {"status": "ok"}, 200


@app.get("/api/status")
def api_status() -> tuple[dict, int]:
    return simulator.get_snapshot(), 200


@app.get("/api/history")
def api_history() -> tuple[dict, int]:
    return {
        "metrics": database.get_recent_metrics(limit=30),
        "events": database.get_recent_events(limit=20),
    }, 200


@app.get("/api/report")
def api_report() -> tuple[dict, int]:
    return database.get_report_summary(), 200


@app.get("/api/report.csv")
def api_report_csv() -> Response:
    csv_content = database.export_report_csv(limit=120)
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=mhe_smartmonitor_report.csv"},
    )


@app.post("/api/control")
def api_control() -> tuple[dict, int]:
    payload = request.get_json(silent=True) or {}
    action = str(payload.get("action", "")).strip().lower()

    actions = {
        "start": simulator.command_start,
        "stop": simulator.command_stop,
        "ack": simulator.acknowledge_alarm,
        "clear": simulator.clear_fault,
        "jam": lambda: simulator.inject_fault("JAM"),
        "slowdown": lambda: simulator.inject_fault("SLOWDOWN"),
        "overload": lambda: simulator.inject_fault("OVERLOAD"),
        "estop": lambda: simulator.inject_fault("STOP"),
    }

    handler = actions.get(action)
    if handler is None:
        return {"ok": False, "error": f"Unsupported action: {action}"}, 400

    handler()
    return {"ok": True, "snapshot": simulator.get_snapshot()}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
