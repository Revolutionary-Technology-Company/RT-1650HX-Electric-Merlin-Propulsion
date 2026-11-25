#!/usr/bin/env python3
"""
RT-1650HX 16-State Hexadecimal Sawtooth Torque & Failover Controller
Native 0.0V - 1.0V analog voltage modulation (0.0625V step resolution, zero DAC latency)
"""

from dataclasses import dataclass
from typing import List

HEX_STEP_V = 0.0625          # 1.0V / 16 discrete states (0x0 to 0xF)
MAX_POWER_KW = 2400.0        # 2.4 MW peak takeoff rating
NOMINAL_PROP_RPM = 1350.0
STACK_COUNT = 4


@dataclass
class StackTelemetry:
    stack_id: int
    healthy: bool
    temp_c: float
    current_a: float


def quantize_to_hex_voltage(normalized_demand: float) -> float:
    """Clamps demand [0.0, 1.0] to nearest 0.0625V RT hexadecimal state."""
    clamped = max(0.0, min(1.0, normalized_demand))
    hex_nibble = round(clamped * 15)
    return round(hex_nibble * HEX_STEP_V, 4)


class MerlinHexController:
    def __init__(self):
        self.stacks: List[StackTelemetry] = [
            StackTelemetry(stack_id=i, healthy=True, temp_c=45.0, current_a=0.0)
            for i in range(1, STACK_COUNT + 1)
        ]

    def compute_stack_voltages(self, throttle_hex_v: float) -> dict:
        """
        Distributes 0.0V-1.0V analog gate modulation across healthy sawtooth stacks.
        Automatically compensates if a stack faults or hits thermal derate (>115C).
        """
        hex_state = int(round(max(0.0, min(1.0, throttle_hex_v)) / HEX_STEP_V))
        requested_kw = (hex_state / 15.0) * MAX_POWER_KW

        active_stacks = [
            s for s in self.stacks if s.healthy and s.temp_c < 115.0
        ]
        if not active_stacks:
            return {"status": "EMERGENCY_SHUTDOWN", "stack_voltages": {}}

        per_stack_max_kw = MAX_POWER_KW / STACK_COUNT
        needed_per_stack_kw = requested_kw / len(active_stacks)

        commands = {}
        for s in self.stacks:
            if s in active_stacks:
                ratio = needed_per_stack_kw / per_stack_max_kw
                commands[f"STACK_{s.stack_id}"] = quantize_to_hex_voltage(ratio)
            else:
                commands[f"STACK_{s.stack_id}"] = 0.0

        return {
            "hex_state": f"0x{hex_state:X}",
            "requested_kw": round(requested_kw, 1),
            "active_stacks": len(active_stacks),
            "stack_voltages": commands,
        }


if __name__ == "__main__":
    ctrl = MerlinHexController()
    print("Nominal 4-Stack Cruise (0.75V / 0xC):", ctrl.compute_stack_voltages(0.75))

    # Simulate Stack 2 fault -> automatic power redistribution across Stacks 1, 3, 4
    ctrl.stacks[1].healthy = False
    print("Stack 2 Fault Failover (0.75V / 0xC):", ctrl.compute_stack_voltages(0.75))
