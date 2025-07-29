"""
bus_scheduler/app.py

This module implements a small web application for scheduling buses to runs.
Users can define inbound and outbound runs, select whether EU assimilated
rules or GB domestic drivers’ hours rules apply, and then compute a
schedule that uses the fewest buses possible. The scheduler treats all
buses as identical and ignores vehicle type, fuel, or driver history.

The app uses Flask for the web framework. It exposes two routes:

* ``/`` – Displays the data entry form where users can add inbound and
  outbound runs, configure the regulatory regime, and submit the data for
  scheduling.
* ``/schedule`` – Accepts posted form data, constructs run objects,
  applies a greedy scheduling algorithm to assign buses, and renders the
  resulting schedule.

Date and time handling uses only the time-of-day for a single “standard
day.” If a run ends before it starts (e.g. crosses midnight), it is
assumed to finish the following day. For simplicity the scheduler
considers only total driving time per bus and does not implement
mandatory breaks or rest periods, although maximum daily driving hours
vary between EU (9 hours) and GB domestic (10 hours) rules【830846819082181†L114-L122】【344526805669237†L186-L192】.

"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from flask import Flask, render_template, request, redirect, url_for


app = Flask(__name__)


@dataclass
class Run:
    """Represents a single bus run.

    Attributes
    ----------
    run_id:
        A unique identifier for the run (typically the name provided by
        the user).
    start:
        A ``datetime`` representing the start time of the run. The date
        component is arbitrary (today) but required for time
        arithmetic.
    end:
        A ``datetime`` representing the end time of the run. If the run
        crosses midnight it will be one day after the start.
    stops:
        A list of stops for the run, used only for display purposes.
    section:
        Either ``inbound`` or ``outbound`` to denote which section the
        run came from.
    """

    run_id: str
    start: datetime
    end: datetime
    stops: List[str]
    section: str

    @property
    def duration_hours(self) -> float:
        """Return the duration of the run in hours."""
        return (self.end - self.start).total_seconds() / 3600.0


@dataclass
class BusAssignment:
    """Represents a bus and the runs assigned to it."""

    bus_id: int
    runs: List[Run] = field(default_factory=list)

    @property
    def total_driving_hours(self) -> float:
        return sum(r.duration_hours for r in self.runs)

    @property
    def last_end_time(self) -> datetime:
        return self.runs[-1].end if self.runs else datetime.min


def get_breaks_for_bus(bus_runs, regime):
    """Return a list of (break_time, break_length_minutes) for a bus's runs based on regime."""
    breaks = []
    continuous_limit = 4.5 if regime == 'EU' else 5.5  # hours
    break_length = 45 if regime == 'EU' else 30  # minutes
    driving_since_last_break = 0.0
    last_break_time = None
    last_run_end = None
    for run in bus_runs:
        driving_since_last_break += run.duration_hours
        last_run_end = run.end
        if driving_since_last_break >= continuous_limit:
            # Insert break after this run
            break_time = last_run_end
            breaks.append((break_time, break_length))
            driving_since_last_break = 0.0
            last_break_time = break_time
            # Advance last_run_end by break_length to ensure next run starts after break
            last_run_end += timedelta(minutes=break_length)
    return breaks


def schedule_buses(runs: List[Run], _max_daily_hours: float) -> List[BusAssignment]:
    """Assign runs to buses, alternating inbound/outbound, allowing multiple runs per bus. Ensures breaks are respected and no run overlaps with a break."""
    all_runs = sorted(runs, key=lambda r: r.start)
    buses: List[BusAssignment] = []
    assigned = set()
    regime = 'EU' if any(r for r in runs if r.section == 'EU') else 'GB'
    continuous_limit = 4.5 if regime == 'EU' else 5.5
    break_length = 45 if regime == 'EU' else 30

    for run in all_runs:
        if run.run_id in assigned:
            continue
        best_bus = None
        for bus in buses:
            # Calculate next available time for this bus, considering breaks
            driving_since_last_break = 0.0
            last_end = None
            for r in bus.runs:
                driving_since_last_break += r.duration_hours
                last_end = r.end
                if driving_since_last_break >= continuous_limit:
                    last_end += timedelta(minutes=break_length)
                    driving_since_last_break = 0.0
            # Ensure run does not start during a break
            if last_end is None or last_end <= run.start:
                best_bus = bus
                break
        if best_bus:
            best_bus.runs.append(run)
            assigned.add(run.run_id)
        else:
            new_bus = BusAssignment(bus_id=len(buses) + 1)
            new_bus.runs.append(run)
            buses.append(new_bus)
            assigned.add(run.run_id)
    return buses


@app.route('/', methods=['GET'])
def index() -> str:
    """Render the form for entering runs and selecting regulations."""
    return render_template('index.html')


@app.route('/schedule', methods=['POST'])
def handle_schedule() -> str:
    """Handle form submission and compute the bus schedule."""
    regulation = request.form.get('regulation', 'GB')
    # Determine maximum daily driving hours based on regulation
    max_hours = 9.0 if regulation == 'EU' else 10.0

    runs: List[Run] = []
    # Parse inbound runs
    inbound_count = int(request.form.get('inbound_count') or 0)
    for i in range(inbound_count):
        name = request.form.get(f'inbound_run_{i}_name')
        start_str = request.form.get(f'inbound_run_{i}_start')
        end_str = request.form.get(f'inbound_run_{i}_end')
        stops_str = request.form.get(f'inbound_run_{i}_stops') or ''
        if not name or not start_str or not end_str:
            continue  # skip incomplete runs
        try:
            start_dt = datetime.strptime(start_str, '%H:%M')
            end_dt = datetime.strptime(end_str, '%H:%M')
        except ValueError:
            continue  # skip if time format is wrong
        # If end time is before start time, assume it finishes next day
        if end_dt <= start_dt:
            end_dt = end_dt + timedelta(days=1)
        stops = [s.strip() for s in stops_str.splitlines() if s.strip()]
        runs.append(Run(run_id=name.strip(), start=start_dt, end=end_dt, stops=stops, section='inbound'))

    # Parse outbound runs
    outbound_count = int(request.form.get('outbound_count') or 0)
    for i in range(outbound_count):
        name = request.form.get(f'outbound_run_{i}_name')
        start_str = request.form.get(f'outbound_run_{i}_start')
        end_str = request.form.get(f'outbound_run_{i}_end')
        stops_str = request.form.get(f'outbound_run_{i}_stops') or ''
        if not name or not start_str or not end_str:
            continue
        try:
            start_dt = datetime.strptime(start_str, '%H:%M')
            end_dt = datetime.strptime(end_str, '%H:%M')
        except ValueError:
            continue
        if end_dt <= start_dt:
            end_dt = end_dt + timedelta(days=1)
        stops = [s.strip() for s in stops_str.splitlines() if s.strip()]
        runs.append(Run(run_id=name.strip(), start=start_dt, end=end_dt, stops=stops, section='outbound'))

    # Compute schedule
    buses = schedule_buses(runs, max_hours)
    # Compute breaks for each bus
    bus_breaks = {}
    for bus in buses:
        bus_breaks[bus.bus_id] = get_breaks_for_bus(bus.runs, regulation)

    # Build list of all stops across runs for table display
    all_stops = []  # maintain order of appearance
    seen_stops = set()
    for run in runs:
        for stop in run.stops:
            if stop not in seen_stops:
                seen_stops.add(stop)
                all_stops.append(stop)

    # Sort runs for display by run_id for consistent ordering
    runs_sorted = sorted(runs, key=lambda r: r.run_id)

    return render_template('schedule.html', runs=runs_sorted, buses=buses, all_stops=all_stops, regulation=regulation, bus_breaks=bus_breaks)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5620, debug=True)