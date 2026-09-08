"""
Rotax 915 iS Engine Specifications & Operating Limits Constants
Target Aircraft: MALE UAV (Medium Altitude Long Endurance UAV)
Problem Statement: SIH 2026 SIH26054
"""

ENGINE_SPECS = {
    "RPM": {"min": 1800, "max": 5800, "nominal": 5400, "unit": "RPM"},
    "EGT": {"min": 750, "max": 950, "nominal": 800, "unit": "°C"},
    "CHT": {"min": 100, "max": 120, "nominal": 110, "unit": "°C"},
    "MAP": {"min": 30, "max": 45, "nominal": 40, "unit": "inHg"},
    "Fuel_Pressure": {"min": 2.9, "max": 3.2, "nominal": 3.0, "unit": "bar"},
    "Oil_Pressure": {"min": 2.0, "max": 5.0, "nominal": 4.0, "unit": "bar"},
    "Vibration": {"min": 1.5, "max": 2.5, "nominal": 2.0, "unit": "G"}
}
