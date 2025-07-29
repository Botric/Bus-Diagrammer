#!/usr/bin/env python3

from app import srt_db, Run, update_srt_from_runs
from datetime import datetime

print("Testing SRT Database Updates with Web Interface Simulation...")
print(f"Initial entries: {len(srt_db.data)}")

# Simulate web interface input - sometimes stops come in as empty or single values
test_runs_web_style = [
    # Run with no stops (empty list)
    Run('WEB1', datetime.strptime('08:00', '%H:%M'), datetime.strptime('09:00', '%H:%M'), 
        [], 'A'),
    # Run with only one stop (not enough for segments)
    Run('WEB2', datetime.strptime('09:15', '%H:%M'), datetime.strptime('10:15', '%H:%M'), 
        ['Single Stop'], 'B'),
    # Run with proper stops
    Run('WEB3', datetime.strptime('10:30', '%H:%M'), datetime.strptime('11:30', '%H:%M'), 
        ['Web Station A', 'Web Station B', 'Web Station C'], 'A')
]

print("\nBefore update:")
for run in test_runs_web_style:
    print(f"Run {run.run_id}: {len(run.stops)} stops - {run.stops}")

# Update SRT database
update_srt_from_runs(test_runs_web_style)

print(f"\nAfter update: {len(srt_db.data)} entries")

# Check if new stations were added
web_stations = ['Web Station A', 'Web Station B', 'Web Station C']
print("\nWeb station entries:")
for station in web_stations:
    count = sum(1 for entry in srt_db.data.values() if station in [entry.from_station, entry.to_station])
    print(f"{station}: {count} entries")

print("\nRecent entries (last 5):")
for key, entry in list(srt_db.data.items())[-5:]:
    print(f"{entry.from_station} -> {entry.to_station}: {entry.duration_minutes} min")
