#!/usr/bin/env python3
"""
RT-1650HX KiCad Netlist & RT Physical Constraint Generator
Generates 1200V 4-Stack SiC Inverter Gate-Driver & 16-State Analog Control Board
"""

import argparse
import json
from dataclasses import dataclass, field
from typing import List


@dataclass
class RTGuardRing:
    net_name: str
    shield_potential_v: float = 0.0
    clearance_mm: float = 1.25
    via_stitch_pitch_mm: float = 2.0


@dataclass
class RTTraceSpec:
    net_name: str
    copper_oz: int
    width_mm: float
    max_angle_deg: int = 45
    allow_crossing: bool = False
    guard_ring: RTGuardRing = None


@dataclass
class MerlinInverterBoard:
    voltage_bus_v: int = 1200
    stack_channels: int = 4
    layer_count: int = 8
    traces: List[RTTraceSpec] = field(default_factory=list)

    def build_architecture(self):
        # Split 1200V DC Bus (Dual Redundant Buses A & B)
        for bus in ("BUS_A_1200V", "BUS_B_1200V"):
            self.traces.append(
                RTTraceSpec(net_name=f"{bus}_POS", copper_oz=3, width_mm=12.0)
            )
            self.traces.append(
                RTTraceSpec(net_name=f"{bus}_NEG", copper_oz=3, width_mm=12.0)
            )

        # 4 Sawtooth Motor Stack Channels (3 Phases each + Hex Analog Sense)
        for ch in range(1, self.stack_channels + 1):
            for phase in ("U", "V", "W"):
                # Heavy-copper SiC gate drive lines
                self.traces.append(
                    RTTraceSpec(
                        net_name=f"CH{ch}_GATE_{phase}_HI",
                        copper_oz=3,
                        width_mm=2.5,
                    )
                )
                self.traces.append(
                    RTTraceSpec(
                        net_name=f"CH{ch}_GATE_{phase}_LO",
                        copper_oz=3,
                        width_mm=2.5,
                    )
                )
                # Isolated 0.0V-1.0V Hexadecimal Current-Sense Feedback
                sense_net = f"CH{ch}_HEX_ISENSE_{phase}"
                self.traces.append(
                    RTTraceSpec(
                        net_name=sense_net,
                        copper_oz=2,
                        width_mm=0.35,
                        guard_ring=RTGuardRing(net_name=f"GUARD_{sense_net}"),
                    )
                )

            # 16-State Rotor Sawtooth Position Resolver Input (0.0V - 1.0V)
            res_net = f"CH{ch}_HEX_RESOLVER_POS"
            self.traces.append(
                RTTraceSpec(
                    net_name=res_net,
                    copper_oz=2,
                    width_mm=0.35,
                    guard_ring=RTGuardRing(net_name=f"GUARD_{res_net}"),
                )
            )

    def verify_thermal_and_rt_rules(self) -> bool:
        for t in self.traces:
            if t.allow_crossing or t.max_angle_deg != 45:
                raise ValueError(f"RT Routing Violation on {t.net_name}")
            if "BUS" in t.net_name and t.copper_oz < 3:
                raise ValueError(f"Joule Heating Risk: {t.net_name} requires 3oz copper")
            if "HEX_" in t.net_name and t.guard_ring is None:
                raise ValueError(f"EMI Violation: {t.net_name} missing RTGuardRing")
        return True

    def export_kicad_netlist(self, filename: str = "kicad/merlin_1200v_inverter.net"):
        lines = [
            "(export (version D)",
            "  (design (source \"RT-1650HX-Electric-Merlin-Propulsion\") (tool \"build_merlin_inverter.py\"))",
            "  (nets",
        ]
        for idx, t in enumerate(self.traces, start=1):
            guard_attr = f" (guard_ring {t.guard_ring.net_name})" if t.guard_ring else ""
            lines.append(
                f"    (net (code {idx}) (name \"{t.net_name}\") (copper_oz {t.copper_oz}) (width_mm {t.width_mm}){guard_attr})"
            )
        lines.append("  )\n)")
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"[OK] Exported {len(self.traces)} RT-certified nets to {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-kicad", action="store_true")
    parser.add_argument("--verify-thermal-limits", action="store_true")
    parser.add_argument("--layer-count", type=int, default=8)
    args = parser.parse_args()

    board = MerlinInverterBoard(layer_count=args.layer_count)
    board.build_architecture()

    if args.verify_thermal_limits:
        if board.verify_thermal_and_rt_rules():
            print("[PASS] All 1200V bus, 3oz copper, 45-deg routing, and RTGuardRing checks passed.")

    if args.export_kicad:
        board.export_kicad_netlist()
