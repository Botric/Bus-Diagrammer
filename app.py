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


def schedule_buses(runs: List[Run], max_daily_hours: float) -> List[BusAssignment]:
    """Assign runs to buses using a greedy algorithm.

    Runs are sorted by start time. For each run we attempt to fit it onto
    an existing bus whose last run finishes before the new run starts and
    whose total driving time plus the run duration does not exceed
    ``max_daily_hours``. If no such bus exists, a new bus is created.

    Parameters
    ----------
    runs:
        A list of ``Run`` objects to schedule.
    max_daily_hours:
        Maximum total driving hours allowed per bus. EU rules allow 9
        hours per day (extendable twice per week to 10)【830846819082181†L114-L122】 while GB domestic rules
        allow 10 hours【344526805669237†L186-L190】.

    Returns
    -------
    List[BusAssignment]
        A list of bus assignments.
    """
    # Sort runs by start time to schedule as early as possible
    runs_sorted = sorted(runs, key=lambda r: (r.start, r.end))
    buses: List[BusAssignment] = []

    for run in runs_sorted:
        assigned = False
        # Try to fit run onto an existing bus
        for bus in buses:
            if bus.last_end_time <= run.start and (bus.total_driving_hours + run.duration_hours) <= max_daily_hours:
                bus.runs.append(run)
                assigned = True
                break
        # If it doesn't fit anywhere, start a new bus
        if not assigned:
            new_bus = BusAssignment(bus_id=len(buses) + 1)
            new_bus.runs.append(run)
            buses.append(new_bus)
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

    return render_template('schedule.html', runs=runs_sorted, buses=buses, all_stops=all_stops, regulation=regulation)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)