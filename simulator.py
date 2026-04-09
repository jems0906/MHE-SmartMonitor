from __future__ import annotations

import random
import threading
import time
from datetime import datetime
from typing import Any

from database import DatabaseManager


class ConveyorSimulator:
    """Simple conveyor + PLC-style state machine simulator."""

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database
        self._lock = threading.Lock()
        self._rng = random.Random()
        self._thread: threading.Thread | None = None
        self._alive = False

        self.commanded_run = True
        self.manual_fault: str | None = None
        self.auto_fault: str | None = None
        self.auto_fault_until = 0.0
        self._last_fault: str | None = None

        self.fault_counts = {
            "JAM": 0,
            "SLOWDOWN": 0,
            "OVERLOAD": 0,
            "STOP": 0,
        }

        self.state: dict[str, Any] = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "throughput_rate": 0.0,
            "conveyor_speed": 0.0,
            "motor_status": "STARTING",
            "health_status": "READY",
            "active_fault": None,
            "current_draw": 0.0,
            "temperature": 25.0,
            "load_pct": 50.0,
            "total_units": 0.0,
            "plc_mode": "INIT",
            "line_state": "INITIALIZING",
            "alarm_code": "ALM-000",
            "alarm_status": "CLEAR",
            "alarm_acknowledged": True,
            "sensors": {
                "start_permissive": True,
                "photoeye_clear": True,
                "drive_ready": True,
                "safety_circuit": True,
            },
            "uptime_seconds": 0,
            "jam_count": 0,
            "slowdown_count": 0,
            "overload_count": 0,
            "stop_count": 0,
            "recommendation": "System boot sequence complete.",
            "alerts": ["System initialized and monitoring started."],
        }

        self.database.log_event(
            "SYSTEM",
            "INFO",
            "MHE SmartMonitor simulation initialized",
            "Conveyor diagnostics engine started.",
        )

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._alive = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def shutdown(self) -> None:
        self._alive = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def command_start(self) -> None:
        with self._lock:
            self.commanded_run = True
        self.database.log_event("COMMAND", "INFO", "Operator commanded conveyor START")

    def command_stop(self) -> None:
        with self._lock:
            self.commanded_run = False
        self.database.log_event("COMMAND", "WARNING", "Operator commanded conveyor STOP")

    def acknowledge_alarm(self) -> None:
        with self._lock:
            active_fault = self.manual_fault or self.auto_fault or self.state.get("active_fault")
            self.state["alarm_acknowledged"] = True
            self.state["alarm_status"] = "ACKNOWLEDGED" if active_fault else "CLEAR"
        self.database.log_event(
            "ACK",
            "INFO",
            f"Alarm acknowledged: {active_fault or 'NO_ACTIVE_FAULT'}",
        )

    def inject_fault(self, fault_name: str) -> None:
        fault = fault_name.upper()
        with self._lock:
            self.manual_fault = fault
            self.state["alarm_acknowledged"] = False
            self.state["alarm_status"] = "UNACKNOWLEDGED"
        self.database.log_event("FAULT", "CRITICAL", f"Manual fault injected: {fault}")

    def clear_fault(self) -> None:
        with self._lock:
            cleared_fault = self.manual_fault or self.auto_fault or self._last_fault
            self.manual_fault = None
            self.auto_fault = None
            self.auto_fault_until = 0.0
            self.state["alarm_acknowledged"] = True
            self.state["alarm_status"] = "CLEAR"
        if cleared_fault:
            self.database.log_event("RECOVERY", "INFO", f"Fault cleared: {cleared_fault}")

    def get_snapshot(self) -> dict[str, Any]:
        with self._lock:
            snapshot = dict(self.state)
            snapshot["fault_counts"] = dict(self.fault_counts)
            return snapshot

    def _run_loop(self) -> None:
        while self._alive:
            self._simulate_step()
            time.sleep(1)

    def _simulate_step(self) -> None:
        with self._lock:
            self._maybe_generate_auto_fault()
            fault = self.manual_fault or self.auto_fault

            load_pct = max(20.0, min(98.0, self.state["load_pct"] + self._rng.uniform(-6.0, 6.0)))
            target_speed = 60.0
            current_draw = 7.5 + (load_pct / 100.0) * 8.5 + self._rng.uniform(-0.8, 0.8)
            temperature = 35.0 + (load_pct / 100.0) * 12.0 + self._rng.uniform(-1.2, 1.2)
            uptime = self.state["uptime_seconds"] + 1

            if self.commanded_run:
                conveyor_speed = target_speed * (0.96 + self._rng.uniform(-0.04, 0.04))
                throughput_rate = conveyor_speed * 1.55 * (load_pct / 100.0)
                motor_status = "RUNNING"
                health_status = "HEALTHY"
                plc_mode = "RUN"
                line_state = "RUNNING"
                alarm_code = "ALM-000"
            else:
                conveyor_speed = 0.0
                throughput_rate = 0.0
                motor_status = "STOPPED"
                health_status = "READY"
                plc_mode = "IDLE"
                line_state = "STOPPED"
                alarm_code = "ALM-IDLE"

            alarm_acknowledged = self.state.get("alarm_acknowledged", True)
            alarm_status = "CLEAR"
            recommendation = "No action required."
            alerts: list[str] = []

            if fault == "SLOWDOWN":
                conveyor_speed *= 0.58
                throughput_rate *= 0.48
                motor_status = "RUNNING - DEGRADED"
                health_status = "WARNING"
                plc_mode = "MONITOR"
                line_state = "DEGRADED"
                alarm_code = "WRN-SLOW-201"
                current_draw += 2.5
                recommendation = "Inspect belt tension and speed feedback sensor."
                alerts.append("Speed below expected setpoint. Possible slip condition.")
            elif fault == "JAM":
                conveyor_speed = 0.0
                throughput_rate = 0.0
                motor_status = "FAULT - JAM"
                health_status = "CRITICAL"
                plc_mode = "FAULT_LOCKOUT"
                line_state = "JAMMED"
                alarm_code = "FLT-JAM-404"
                current_draw += 5.5
                recommendation = "Clear the jam point and verify photo-eye alignment."
                alerts.append("Downstream jam detected. Material accumulation rising.")
            elif fault == "OVERLOAD":
                conveyor_speed *= 0.35
                throughput_rate *= 0.22
                motor_status = "FAULT - OVERLOAD"
                health_status = "CRITICAL"
                plc_mode = "FAULT_LOCKOUT"
                line_state = "OVERLOAD"
                alarm_code = "FLT-AMP-330"
                current_draw += 7.0
                temperature += 6.5
                recommendation = "Reduce line load and inspect motor current draw."
                alerts.append("Motor current above safe threshold. Overload trip pending.")
            elif fault == "STOP":
                conveyor_speed = 0.0
                throughput_rate = 0.0
                motor_status = "E-STOP ACTIVE"
                health_status = "CRITICAL"
                plc_mode = "EMERGENCY_STOP"
                line_state = "SAFETY_STOP"
                alarm_code = "ESTOP-001"
                current_draw = 0.0
                recommendation = "Reset the emergency stop circuit and verify guards."
                alerts.append("Safety circuit opened. Conveyor motion inhibited.")

            if fault:
                alarm_status = "ACKNOWLEDGED" if alarm_acknowledged else "UNACKNOWLEDGED"

            if self.commanded_run and not fault and load_pct > 88:
                health_status = "WARNING"
                line_state = "HIGH_LOAD"
                alarm_code = "WRN-LOAD-188"
                alerts.append("Load is trending high; monitor for overload.")
                recommendation = "Consider reducing infeed rate."

            sensors = {
                "start_permissive": fault != "STOP",
                "photoeye_clear": fault != "JAM",
                "drive_ready": fault not in {"OVERLOAD", "STOP"},
                "safety_circuit": fault != "STOP",
            }

            if self.commanded_run and not fault:
                self.state["total_units"] += throughput_rate / 60.0

            snapshot = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "throughput_rate": round(throughput_rate, 2),
                "conveyor_speed": round(conveyor_speed, 2),
                "motor_status": motor_status,
                "health_status": health_status,
                "active_fault": fault,
                "current_draw": round(max(0.0, current_draw), 2),
                "temperature": round(max(20.0, temperature), 2),
                "load_pct": round(load_pct, 2),
                "total_units": round(self.state["total_units"], 2),
                "plc_mode": plc_mode,
                "line_state": line_state,
                "alarm_code": alarm_code,
                "alarm_status": alarm_status,
                "alarm_acknowledged": alarm_acknowledged,
                "sensors": sensors,
                "uptime_seconds": uptime,
                "jam_count": self.fault_counts["JAM"],
                "slowdown_count": self.fault_counts["SLOWDOWN"],
                "overload_count": self.fault_counts["OVERLOAD"],
                "stop_count": self.fault_counts["STOP"],
                "recommendation": recommendation,
                "alerts": alerts or ["System within expected operating range."],
            }

            self.state.update(snapshot)
            self._track_fault_transitions(fault)
            self.database.log_metric(self.state)

    def _maybe_generate_auto_fault(self) -> None:
        now = time.monotonic()

        if self.manual_fault:
            return

        if self.auto_fault and now >= self.auto_fault_until:
            self.auto_fault = None
            self.auto_fault_until = 0.0

        if self.auto_fault or not self.commanded_run:
            return

        roll = self._rng.random()
        if roll < 0.015:
            self.auto_fault = "SLOWDOWN"
            self.auto_fault_until = now + self._rng.uniform(8, 14)
        elif roll < 0.023:
            self.auto_fault = "JAM"
            self.auto_fault_until = now + self._rng.uniform(6, 10)
        elif roll < 0.03:
            self.auto_fault = "OVERLOAD"
            self.auto_fault_until = now + self._rng.uniform(5, 9)

    def _track_fault_transitions(self, fault: str | None) -> None:
        if fault == self._last_fault:
            return

        if fault:
            self.fault_counts[fault] += 1
            self.state["alarm_acknowledged"] = False
            self.state["alarm_status"] = "UNACKNOWLEDGED"
            self.database.log_event(
                "FAULT",
                "CRITICAL" if fault in {"JAM", "OVERLOAD", "STOP"} else "WARNING",
                f"{fault} detected",
                self.state["recommendation"],
            )
        elif self._last_fault:
            self.state["alarm_acknowledged"] = True
            self.state["alarm_status"] = "CLEAR"
            self.database.log_event(
                "RECOVERY",
                "INFO",
                f"{self._last_fault} condition cleared",
                "System returned to nominal state.",
            )

        self._last_fault = fault
