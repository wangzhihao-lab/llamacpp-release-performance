// Prints macOS ProcessInfo.thermalState: 0 nominal, 1 fair, 2 serious, 3 critical.
// Build: mkdir -p scripts/analysis/bin && swiftc -O -o scripts/analysis/bin/thermal_state scripts/analysis/thermal_state.swift
import Foundation
print(ProcessInfo.processInfo.thermalState.rawValue)
