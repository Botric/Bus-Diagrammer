#!/usr/bin/env python3

from app import Run, schedule_buses, get_breaks_for_bus
from datetime import datetime

# Test data
test_runs = [
    Run('101', datetime.strptime('08:00', '%H:%M'), datetime.strptime('09:00', '%H:%M'), ['Stop A', 'Stop B', 'Stop C'], 'A'),
    Run('102', datetime.strptime('09:15', '%H:%M'), datetime.strptime('10:15', '%H:%M'), ['Stop C', 'Stop B', 'Stop A'], 'B')
]

# Test scheduling directly
print("Testing scheduling algorithm...")
buses = schedule_buses(test_runs, 'GB', 15, 0, None, True, {})
print(f'Buses generated: {len(buses)}')

for bus in buses:
    print(f'Bus {bus.bus_id}: {len(bus.runs)} runs')
    for run in bus.runs:
        print(f'  - {run.run_id}: {run.start.strftime("%H:%M")} - {run.end.strftime("%H:%M")}')

# Test timetable data structure
print("\nTesting timetable data structure...")
all_stops = []
seen_stops = set()
timetable_data = {}

for run in test_runs:
    for stop in run.stops:
        if stop not in seen_stops:
            seen_stops.add(stop)
            all_stops.append(stop)

# Second pass: build timetable data with stop as key, runs as values
for stop in all_stops:
    timetable_data[stop] = []
    for run in test_runs:
        if stop in run.stops:
            stop_index = run.stops.index(stop)
            time = run.get_stop_time(stop_index)
        else:
            time = None
        timetable_data[stop].append({
            'run_id': run.run_id,
            'time': time,
            'section': run.section
        })

print("Timetable data:")
for stop, runs in timetable_data.items():
    print(f"{stop}: {runs}")
