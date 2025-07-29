#!/usr/bin/env python3

from app import srt_db, Run, update_srt_from_runs
from datetime import datetime

print("Testing SRT Database Updates...")
print(f"Initial entries: {len(srt_db.data)}")

# Create test runs with new locations
test_runs = [
    Run('TEST1', datetime.strptime('08:00', '%H:%M'), datetime.strptime('09:00', '%H:%M'), 
        ['New Station A', 'New Station B', 'New Station C'], 'A'),
    Run('TEST2', datetime.strptime('09:15', '%H:%M'), datetime.strptime('10:15', '%H:%M'), 
        ['New Station C', 'New Station D', 'New Station E'], 'B')
]

print("\nBefore update:")
for run in test_runs:
    print(f"Run {run.run_id}: {' -> '.join(run.stops)}")

# Update SRT database
update_srt_from_runs(test_runs)

print(f"\nAfter update: {len(srt_db.data)} entries")

# Check if new stations were added
new_stations = ['New Station A', 'New Station B', 'New Station C', 'New Station D', 'New Station E']
print("\nNew station entries:")
for station in new_stations:
    count = sum(1 for entry in srt_db.data.values() if station in [entry.from_station, entry.to_station])
    print(f"{station}: {count} entries")

print("\nSample new entries:")
for key, entry in list(srt_db.data.items())[-10:]:
    if any(station in [entry.from_station, entry.to_station] for station in new_stations):
        print(f"{entry.from_station} -> {entry.to_station}: {entry.duration_minutes} min")
