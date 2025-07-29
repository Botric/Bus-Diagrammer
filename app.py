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


def get_breaks_for_bus(bus_runs, regime, max_continuous_time: Optional[float] = None, min_break_extension: int = 0):
    """Return a list of (break_time, break_length_minutes, break_type) for a bus's runs based on regime."""
    breaks = []
    
    # Use custom continuous limit if provided, otherwise use regulation default
    if max_continuous_time is not None:
        continuous_limit = max_continuous_time
    else:
        continuous_limit = 4.5 if regime == 'EU' else 5.5  # hours
    
    driving_since_last_break = 0.0
    
    for i, run in enumerate(bus_runs):
        # Check if we need a break before this run
        if driving_since_last_break > 0 and driving_since_last_break + run.duration_hours > continuous_limit:
            # Need a break before this run
            if regime == 'EU':
                # EU rules: 45 minutes total (can be split but use single break for simplicity)
                base_break_duration = 45
                break_type = "EU Break"
            else:
                # GB domestic: 30 minutes minimum, cannot be split
                base_break_duration = 30
                break_type = "GB Break"
            
            total_break_duration = base_break_duration + min_break_extension
            breaks.append((run.start - timedelta(minutes=total_break_duration), total_break_duration, break_type))
            driving_since_last_break = 0.0
        
        driving_since_last_break += run.duration_hours
    
    return breaks


def schedule_buses(runs: List[Run], regime: str, min_layover_time: int = 15, 
                  min_break_extension: int = 0, max_continuous_time: Optional[float] = None,
                  prefer_alternating: bool = True, terminal_layovers: Dict[str, int] = None) -> List[BusAssignment]:
    """Assign runs to buses, respecting breaks, regime rules, and custom configuration."""
    all_runs = sorted(runs, key=lambda r: r.start)
    buses: List[BusAssignment] = []
    assigned = set()
    
    # Use custom continuous limit if provided, otherwise use regulation default
    if max_continuous_time is not None:
        continuous_limit = max_continuous_time
    else:
        continuous_limit = 4.5 if regime == 'EU' else 5.5

    # Initialize terminal layovers dictionary if not provided
    if terminal_layovers is None:
        terminal_layovers = {}
    dead_time_minutes = min_layover_time

    for run in all_runs:
        if run.run_id in assigned:
            continue
        
        best_bus = None
        for bus in buses:
            if not bus.runs:
                best_bus = bus
                break
                
            # Calculate when this bus will be available considering breaks and dead time
            driving_since_last_break = 0.0
            last_end = None
            
            for r in bus.runs:
                driving_since_last_break += r.duration_hours
                last_end = r.end
            
            # Check if we need a break after the last run for the new run
            if driving_since_last_break + run.duration_hours > continuous_limit:
                # Need a break before the new run
                base_break_duration = 45 if regime == 'EU' else 30
                break_duration = base_break_duration + min_break_extension
                # Bus available after last run + dead time + break time
                if last_end:
                    last_end += timedelta(minutes=dead_time_minutes + break_duration)
            else:
                # Determine layover time based on terminal
                if last_end and bus.runs:
                    last_run = bus.runs[-1]
                    # Use the end terminal of the last run for layover calculation
                    if last_run.stops:
                        end_terminal = last_run.stops[-1]
                        terminal_layover = get_layover_time_for_terminal(end_terminal, terminal_layovers, dead_time_minutes)
                        last_end += timedelta(minutes=terminal_layover)
                    else:
                        last_end += timedelta(minutes=dead_time_minutes)
                elif last_end:
                    last_end += timedelta(minutes=dead_time_minutes)
            
            # Check if bus is available and prefer alternating inbound/outbound
            if last_end is None or last_end <= run.start:
                # Prefer alternating sections to minimize dead runs (if enabled)
                if prefer_alternating and bus.runs and bus.runs[-1].section != run.section:
                    best_bus = bus
                    break
                elif not best_bus:
                    best_bus = bus
        
        if best_bus:
            best_bus.runs.append(run)
            assigned.add(run.run_id)
        else:
            new_bus = BusAssignment(bus_id=len(buses) + 1)
            new_bus.runs.append(run)
            buses.append(new_bus)
            assigned.add(run.run_id)
    
    return buses


def get_layover_time_for_terminal(terminal: str, terminal_layovers: Dict[str, int], default_layover: int) -> int:
    """Get the layover time for a specific terminal, falling back to default if not specified."""
    # Clean terminal name to match form field names
    clean_terminal = terminal.replace(' ', '_').replace('(', '').replace(')', '')
    return terminal_layovers.get(clean_terminal, default_layover)


@app.route('/', methods=['GET'])
def index() -> str:
    """Render the form for entering runs and selecting regulations."""
    return render_template('index.html')


@app.route('/schedule', methods=['POST'])
def handle_schedule() -> str:
    """Handle form submission and redirect to configuration page or directly generate schedule."""
    regulation = request.form.get('regulation', 'GB')
    skip_configuration = request.form.get('skip_configuration') == 'true'
    
    runs: List[Run] = []
    
    # Parse inbound runs
    inbound_count = int(request.form.get('inbound_count') or 0)
    for i in range(inbound_count):
        name = request.form.get(f'inbound_run_{i}_name')
        start_str = request.form.get(f'inbound_run_{i}_start')
        end_str = request.form.get(f'inbound_run_{i}_end')
        stops_str = request.form.get(f'inbound_run_{i}_stops') or ''
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
    
    if skip_configuration:
        # Generate schedule directly with default parameters
        return generate_schedule_with_defaults(runs, regulation)
    else:
        # Redirect to configuration page
        return render_template('configure.html', runs=runs, regulation=regulation)


@app.route('/generate', methods=['POST'])
def generate_schedule() -> str:
    """Generate the final bus schedule with custom configuration."""
    regulation = request.form.get('regulation', 'GB')
    
    # Get configuration parameters
    min_layover_time = int(request.form.get('min_layover_time', 15))
    min_break_extension = int(request.form.get('min_break_extension', 0))
    max_continuous_time_str = request.form.get('max_continuous_time', 'default')
    max_continuous_time = None if max_continuous_time_str == 'default' else float(max_continuous_time_str)
    prefer_alternating = request.form.get('prefer_alternating', 'true') == 'true'
    
    # Parse terminal-specific layover times
    terminal_layovers = {}
    use_terminal_layovers = request.form.get('use_terminal_layovers') == 'true'
    if use_terminal_layovers:
        for key, value in request.form.items():
            if key.startswith('terminal_layover_'):
                terminal_name = key.replace('terminal_layover_', '')
                try:
                    terminal_layovers[terminal_name] = int(value)
                except ValueError:
                    pass  # Skip invalid values
    
    runs: List[Run] = []
    
    # Parse runs from hidden form fields
    inbound_count = int(request.form.get('inbound_count') or 0)
    for i in range(inbound_count):
        name = request.form.get(f'inbound_run_{i}_name')
        start_str = request.form.get(f'inbound_run_{i}_start')
        end_str = request.form.get(f'inbound_run_{i}_end')
        stops_str = request.form.get(f'inbound_run_{i}_stops') or ''
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
        runs.append(Run(run_id=name.strip(), start=start_dt, end=end_dt, stops=stops, section='inbound'))
    
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
    
    # Generate schedule with custom parameters
    buses = schedule_buses(runs, regulation, min_layover_time, min_break_extension, 
                          max_continuous_time, prefer_alternating, terminal_layovers)
    
    bus_breaks = {}
    run_to_bus = {}  # Create a lookup dictionary for run_id to bus_id
    for bus in buses:
        bus_breaks[bus.bus_id] = get_breaks_for_bus(bus.runs, regulation, max_continuous_time, min_break_extension)
        for run in bus.runs:
            run_to_bus[run.run_id] = bus.bus_id
    
    all_stops = []
    seen_stops = set()
    for run in runs:
        for stop in run.stops:
            if stop not in seen_stops:
                seen_stops.add(stop)
                all_stops.append(stop)
    
    # Keep runs in the original input order instead of sorting by run_id
    return render_template('schedule.html', runs=runs, buses=buses, all_stops=all_stops, 
                          regulation=regulation, bus_breaks=bus_breaks, run_to_bus=run_to_bus,
                          min_layover_time=min_layover_time, min_break_extension=min_break_extension,
                          terminal_layovers=terminal_layovers)


def generate_schedule_with_defaults(runs: List[Run], regulation: str) -> str:
    """Generate schedule with default parameters when skipping configuration."""
    # Use default parameters
    min_layover_time = 15
    min_break_extension = 0
    max_continuous_time = None
    prefer_alternating = True
    terminal_layovers = {}
    
    # Generate schedule with default parameters
    buses = schedule_buses(runs, regulation, min_layover_time, min_break_extension, 
                          max_continuous_time, prefer_alternating, terminal_layovers)
    
    bus_breaks = {}
    run_to_bus = {}  # Create a lookup dictionary for run_id to bus_id
    for bus in buses:
        bus_breaks[bus.bus_id] = get_breaks_for_bus(bus.runs, regulation, max_continuous_time, min_break_extension)
        for run in bus.runs:
            run_to_bus[run.run_id] = bus.bus_id
    
    all_stops = []
    seen_stops = set()
    for run in runs:
        for stop in run.stops:
            if stop not in seen_stops:
                seen_stops.add(stop)
                all_stops.append(stop)
    
    # Keep runs in the original input order instead of sorting by run_id
    return render_template('schedule.html', runs=runs, buses=buses, all_stops=all_stops, 
                          regulation=regulation, bus_breaks=bus_breaks, run_to_bus=run_to_bus,
                          min_layover_time=min_layover_time, min_break_extension=min_break_extension)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5620, debug=True)