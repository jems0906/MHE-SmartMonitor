from __future__ import annotations

import csv
import io
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any


class DatabaseManager:
    def __init__(self, db_path: str | Path = "smartmonitor.db") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metric_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    throughput_rate REAL NOT NULL,
                    conveyor_speed REAL NOT NULL,
                    motor_status TEXT NOT NULL,
                    health_status TEXT NOT NULL,
                    active_fault TEXT,
                    current_draw REAL NOT NULL,
                    temperature REAL NOT NULL,
                    load_pct REAL NOT NULL,
                    total_units REAL NOT NULL,
                    plc_mode TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS event_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT
                );
                """
            )
            connection.commit()

    def log_metric(self, snapshot: dict[str, Any]) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO metric_history (
                    timestamp,
                    throughput_rate,
                    conveyor_speed,
                    motor_status,
                    health_status,
                    active_fault,
                    current_draw,
                    temperature,
                    load_pct,
                    total_units,
                    plc_mode
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot["timestamp"],
                    snapshot["throughput_rate"],
                    snapshot["conveyor_speed"],
                    snapshot["motor_status"],
                    snapshot["health_status"],
                    snapshot["active_fault"],
                    snapshot["current_draw"],
                    snapshot["temperature"],
                    snapshot["load_pct"],
                    snapshot["total_units"],
                    snapshot["plc_mode"],
                ),
            )
            connection.commit()

    def log_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        details: str = "",
    ) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO event_logs (timestamp, event_type, severity, message, details)
                VALUES (datetime('now', 'localtime'), ?, ?, ?, ?)
                """,
                (event_type, severity, message, details),
            )
            connection.commit()

    def get_recent_metrics(self, limit: int = 30) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT timestamp, throughput_rate, conveyor_speed, motor_status,
                       health_status, active_fault, current_draw, temperature,
                       load_pct, total_units, plc_mode
                FROM metric_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in reversed(rows)]

    def get_recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT timestamp, event_type, severity, message, details
                FROM event_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]

    def get_report_summary(self) -> dict[str, Any]:
        with closing(self._connect()) as connection:
            metric_summary = connection.execute(
                """
                SELECT COUNT(*) AS samples,
                       ROUND(AVG(throughput_rate), 2) AS avg_throughput,
                       ROUND(MAX(throughput_rate), 2) AS peak_throughput,
                       ROUND(AVG(CASE WHEN plc_mode IN ('RUN', 'MONITOR') THEN 100.0 ELSE 0.0 END), 2) AS availability_pct,
                       ROUND(MAX(temperature), 2) AS peak_temperature
                FROM metric_history
                """
            ).fetchone()

            event_summary = connection.execute(
                """
                SELECT COUNT(*) AS total_events,
                       COALESCE(SUM(CASE WHEN severity = 'CRITICAL' THEN 1 ELSE 0 END), 0) AS critical_events,
                       COALESCE(SUM(CASE WHEN severity = 'WARNING' THEN 1 ELSE 0 END), 0) AS warning_events
                FROM event_logs
                """
            ).fetchone()

            dominant_fault = connection.execute(
                """
                SELECT COALESCE(active_fault, 'NORMAL') AS fault_name,
                       COUNT(*) AS fault_count
                FROM metric_history
                GROUP BY COALESCE(active_fault, 'NORMAL')
                ORDER BY fault_count DESC
                LIMIT 1
                """
            ).fetchone()

        return {
            "samples": int(metric_summary["samples"] or 0),
            "avg_throughput": float(metric_summary["avg_throughput"] or 0.0),
            "peak_throughput": float(metric_summary["peak_throughput"] or 0.0),
            "availability_pct": float(metric_summary["availability_pct"] or 0.0),
            "peak_temperature": float(metric_summary["peak_temperature"] or 0.0),
            "critical_events": int(event_summary["critical_events"] or 0),
            "warning_events": int(event_summary["warning_events"] or 0),
            "total_events": int(event_summary["total_events"] or 0),
            "dominant_fault": dominant_fault["fault_name"] if dominant_fault else "NORMAL",
        }

    def export_report_csv(self, limit: int = 120) -> str:
        summary = self.get_report_summary()
        metrics = self.get_recent_metrics(limit=limit)
        events = self.get_recent_events(limit=20)

        buffer = io.StringIO()
        writer = csv.writer(buffer)

        writer.writerow(["MHE SmartMonitor Maintenance Report"])
        writer.writerow(["Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow([])
        writer.writerow(["KPI", "Value"])
        writer.writerow(["Samples", summary["samples"]])
        writer.writerow(["Average Throughput", summary["avg_throughput"]])
        writer.writerow(["Peak Throughput", summary["peak_throughput"]])
        writer.writerow(["Availability %", summary["availability_pct"]])
        writer.writerow(["Peak Temperature", summary["peak_temperature"]])
        writer.writerow(["Critical Events", summary["critical_events"]])
        writer.writerow(["Warning Events", summary["warning_events"]])
        writer.writerow(["Dominant Fault", summary["dominant_fault"]])
        writer.writerow([])
        writer.writerow(["Recent Metrics"])
        writer.writerow([
            "timestamp",
            "throughput_rate",
            "conveyor_speed",
            "motor_status",
            "health_status",
            "active_fault",
            "current_draw",
            "temperature",
            "load_pct",
            "total_units",
            "plc_mode",
        ])

        for metric in metrics:
            writer.writerow([
                metric["timestamp"],
                metric["throughput_rate"],
                metric["conveyor_speed"],
                metric["motor_status"],
                metric["health_status"],
                metric["active_fault"],
                metric["current_draw"],
                metric["temperature"],
                metric["load_pct"],
                metric["total_units"],
                metric["plc_mode"],
            ])

        writer.writerow([])
        writer.writerow(["Recent Events"])
        writer.writerow(["timestamp", "event_type", "severity", "message", "details"])
        for event in events:
            writer.writerow([
                event["timestamp"],
                event["event_type"],
                event["severity"],
                event["message"],
                event["details"],
            ])

        return buffer.getvalue()

