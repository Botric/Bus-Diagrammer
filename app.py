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

# Full SRT Database implementation
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass

@dataclass
class SRTEntry:
    from_station: str
    to_station: str
    duration_minutes: int
    last_updated: str

class SRTDatabase:
    def __init__(self, database_file: str = "srt_database.json"):
        self.database_file = database_file
        self.data: Dict[str, SRTEntry] = {}
        self.load_database()
    
    def _make_key(self, from_station: str, to_station: str) -> str:
        from_norm = from_station.strip().lower()
        to_norm = to_station.strip().lower()
        return f"{from_norm}|{to_norm}"
    
    def load_database(self):
        if os.path.exists(self.database_file):
            try:
                with open(self.database_file, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                self.data = {}
                for key, entry_dict in raw_data.items():
                    self.data[key] = SRTEntry(**entry_dict)
            except Exception as e:
                print(f"Warning: Could not load SRT database: {e}")
                self.data = {}
        else:
            self.data = {}
    
    def save_database(self):
        try:
            raw_data = {}
            for key, entry in self.data.items():
                raw_data[key] = {
                    'from_station': entry.from_station,
                    'to_station': entry.to_station,
                    'duration_minutes': entry.duration_minutes,
                    'last_updated': entry.last_updated
                }
            with open(self.database_file, 'w', encoding='utf-8') as f:
                json.dump(raw_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save SRT database: {e}")
    
    def get_travel_time(self, from_station: str, to_station: str) -> Optional[int]:
        key = self._make_key(from_station, to_station)
        entry = self.data.get(key)
        return entry.duration_minutes if entry else None
    
    def update_travel_time(self, from_station: str, to_station: str, duration_minutes: int):
        key = self._make_key(from_station, to_station)
        current_time = datetime.now().isoformat()
        
        existing_entry = self.data.get(key)
        if existing_entry is None or duration_minutes > existing_entry.duration_minutes:
            self.data[key] = SRTEntry(
                from_station=from_station,
                to_station=to_station,
                duration_minutes=duration_minutes,
                last_updated=current_time
            )
            self.save_database()
    
    def update_from_runs(self, runs: List):
        for run in runs:
            if len(run.stops) < 2:
                continue
            
            # Check if run has timing data for each stop
            if hasattr(run, 'stop_times') and run.stop_times and len(run.stop_times) == len(run.stops):
                self._update_from_timetable(run.stops, run.stop_times)
            else:
                self._update_from_duration_only(run)
    
    def _update_from_timetable(self, stops: List[str], stop_times: List[str]):
        parsed_times = []
        for time_str in stop_times:
            try:
                if len(time_str.split(':')) == 2:
                    time_obj = datetime.strptime(time_str, '%H:%M')
                else:
                    time_obj = datetime.strptime(time_str, '%H:%M:%S')
                parsed_times.append(time_obj)
            except (ValueError, AttributeError):
                return self._update_from_duration_only_with_stops(stops, len(stops) * 17)
        
        for i in range(len(stops) - 1):
            from_station = stops[i]
            to_station = stops[i + 1]
            
            time_diff = parsed_times[i + 1] - parsed_times[i]
            if time_diff.total_seconds() < 0:
                time_diff += timedelta(days=1)
            
            duration_minutes = int(time_diff.total_seconds() / 60)
            if 1 <= duration_minutes <= 120:
                self.update_travel_time(from_station, to_station, duration_minutes)
    
    def _update_from_duration_only(self, run):
        total_duration_minutes = int((run.end - run.start).total_seconds() / 60)
        num_segments = len(run.stops) - 1
        if num_segments > 0:
            time_per_segment = total_duration_minutes // num_segments
            for i in range(len(run.stops) - 1):
                from_station = run.stops[i]
                to_station = run.stops[i + 1]
                self.update_travel_time(from_station, to_station, time_per_segment)
    
    def _update_from_duration_only_with_stops(self, stops: List[str], total_duration_minutes: int):
        num_segments = len(stops) - 1
        if num_segments > 0:
            time_per_segment = total_duration_minutes // num_segments
            for i in range(len(stops) - 1):
                from_station = stops[i]
                to_station = stops[i + 1]
                self.update_travel_time(from_station, to_station, time_per_segment)
    
    def get_all_stations(self) -> List[str]:
        stations = set()
        for entry in self.data.values():
            stations.add(entry.from_station)
            stations.add(entry.to_station)
        return sorted(list(stations))
    
    def get_statistics(self) -> Dict:
        return {
            'total_entries': len(self.data),
            'total_stations': len(self.get_all_stations()),
            'last_updated': max([entry.last_updated for entry in self.data.values()]) if self.data else None
        }

srt_db = SRTDatabase()


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
    stop_times:
        Optional list of time strings for each stop (e.g., ['08:00', '08:15', '08:30']).
        Used for accurate SRT calculation when available.
    """

    run_id: str
    start: datetime
    end: datetime
    stops: List[str]
    section: str
    stop_times: Optional[List[str]] = None

    @property
    def duration_hours(self) -> float:
        """Return the duration of the run in hours."""
        return (self.end - self.start).total_seconds() / 3600.0
    
    def get_stop_time(self, stop_index: int) -> str:
        """Get the time for a specific stop, either from stop_times or calculated."""
        if self.stop_times and stop_index < len(self.stop_times):
            return self.stop_times[stop_index]
        
        # Calculate estimated time based on position in route
        if len(self.stops) <= 1:
            return self.start.strftime('%H:%M')
            
        total_duration_minutes = (self.end - self.start).total_seconds() / 60
        segments = len(self.stops) - 1
        time_per_segment = total_duration_minutes / segments
        estimated_minutes = stop_index * time_per_segment
        
        estimated_time = self.start + timedelta(minutes=estimated_minutes)
        return estimated_time.strftime('%H:%M')


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
                
            # Calculate when this bus will be available considering breaks, layover, and travel time
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
                # Determine layover time based on terminal and add travel time
                if last_end and bus.runs:
                    last_run = bus.runs[-1]
                    
                    # Calculate travel time between runs
                    travel_time = calculate_travel_time_between_runs(last_run, run)
                    
                    # Use the end terminal of the last run for layover calculation
                    if last_run.stops:
                        end_terminal = last_run.stops[-1]
                        terminal_layover = get_layover_time_for_terminal(end_terminal, terminal_layovers, dead_time_minutes)
                        # Total time = layover + travel time (travel time accounts for deadheading)
                        total_time = max(terminal_layover, travel_time)
                        last_end += timedelta(minutes=total_time)
                    else:
                        # No stop info, use default layover + estimated travel time
                        last_end += timedelta(minutes=dead_time_minutes + travel_time)
                elif last_end:
                    # No previous runs, just use default layover
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


def calculate_travel_time_between_runs(last_run: Run, next_run: Run) -> int:
    """
    Calculate travel time between the end of one run and start of another.
    Returns time in minutes, or 0 if runs connect directly.
    """
    if not last_run.stops or not next_run.stops:
        return 0  # Can't calculate without stop information
    
    last_end_station = last_run.stops[-1]
    next_start_station = next_run.stops[0]
    
    # If runs connect directly (end station = start station), no travel time needed
    if last_end_station.lower().strip() == next_start_station.lower().strip():
        return 0
    
    # Look up travel time in SRT database
    travel_time = srt_db.get_travel_time(last_end_station, next_start_station)
    
    if travel_time is not None:
        return travel_time
    
    # If no SRT data available, estimate based on a default speed
    # This is a fallback - in practice you'd want actual routing data
    return 15  # Default 15 minutes for unknown routes


def update_srt_from_runs(runs: List[Run]):
    """Update the SRT database with timing data from the input runs."""
    srt_db.update_from_runs(runs)


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
        stop_times_str = request.form.get(f'inbound_run_{i}_stop_times') or ''
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
        
        # Parse stop times if available
        stop_times = None
        if stop_times_str:
            stop_times = [t.strip() for t in stop_times_str.split(',') if t.strip()]
            # Only use stop times if we have the same number as stops
            if len(stop_times) != len(stops):
                stop_times = None
        
        runs.append(Run(run_id=name.strip(), start=start_dt, end=end_dt, stops=stops, section='inbound', stop_times=stop_times))
    
    # Parse outbound runs
    outbound_count = int(request.form.get('outbound_count') or 0)
    for i in range(outbound_count):
        name = request.form.get(f'outbound_run_{i}_name')
        start_str = request.form.get(f'outbound_run_{i}_start')
        end_str = request.form.get(f'outbound_run_{i}_end')
        stops_str = request.form.get(f'outbound_run_{i}_stops') or ''
        stop_times_str = request.form.get(f'outbound_run_{i}_stop_times') or ''
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
        
        # Parse stop times if available
        stop_times = None
        if stop_times_str:
            stop_times = [t.strip() for t in stop_times_str.split(',') if t.strip()]
            # Only use stop times if we have the same number as stops
            if len(stop_times) != len(stops):
                stop_times = None
                
        runs.append(Run(run_id=name.strip(), start=start_dt, end=end_dt, stops=stops, section='outbound', stop_times=stop_times))
    
    # Update SRT database with timing data from input runs
    update_srt_from_runs(runs)
    
    if skip_configuration:
        # Generate schedule directly with default parameters
        return generate_schedule_with_defaults(runs, regulation)
    else:
        # Extract all unique terminal stops from runs
        terminals = set()
        for run in runs:
            if run.stops:
                # First and last stops are terminals
                terminals.add(run.stops[0])
                terminals.add(run.stops[-1])
        
        # Sort terminals alphabetically for consistent ordering
        terminal_list = sorted(list(terminals))
        
        # Redirect to configuration page
        return render_template('configure.html', runs=runs, regulation=regulation, terminals=terminal_list)


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
    run_count = int(request.form.get('run_count', 0))
    for i in range(run_count):
        run_id = request.form.get(f'run_{i}_id')
        start_str = request.form.get(f'run_{i}_start')
        end_str = request.form.get(f'run_{i}_end')
        section = request.form.get(f'run_{i}_section')
        stops_str = request.form.get(f'run_{i}_stops', '')
        stop_times_str = request.form.get(f'run_{i}_stop_times', '')
        
        if not run_id or not start_str or not end_str or not section:
            continue
            
        try:
            start_dt = datetime.strptime(start_str, '%H:%M')
            end_dt = datetime.strptime(end_str, '%H:%M')
        except ValueError:
            continue
            
        if end_dt <= start_dt:
            end_dt = end_dt + timedelta(days=1)
            
        stops = [s.strip() for s in stops_str.split('|') if s.strip()]
        
        # Parse stop times if available
        stop_times = None
        if stop_times_str:
            stop_times = [t.strip() for t in stop_times_str.split(',') if t.strip()]
            if len(stop_times) != len(stops):
                stop_times = None
                
        runs.append(Run(run_id=run_id.strip(), start=start_dt, end=end_dt, stops=stops, section=section, stop_times=stop_times))
    
    # Update SRT database with timing data from input runs
    update_srt_from_runs(runs)
    
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
    
    # Build timetable data organized by stops (rows) with runs (columns)
    timetable_data = {}
    
    # First pass: collect all unique stops in order
    for run in runs:
        for stop in run.stops:
            if stop not in seen_stops:
                seen_stops.add(stop)
                all_stops.append(stop)
    
    # Second pass: build timetable data with stop as key, runs as values
    for stop in all_stops:
        timetable_data[stop] = []
        for run in runs:
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

    # Keep runs in the original input order instead of sorting by run_id
    return render_template('schedule_modern.html', runs=runs, buses=buses, all_stops=all_stops, 
                          regulation=regulation, bus_breaks=bus_breaks, run_to_bus=run_to_bus,
                          min_layover_time=min_layover_time, min_break_extension=min_break_extension,
                          terminal_layovers=terminal_layovers, timetable_data=timetable_data)
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
    # Build timetable data with actual stop times - structure for schedule_modern.html
    timetable_data = {}
    for run in runs:
        for i, stop in enumerate(run.stops):
            if stop not in seen_stops:
                seen_stops.add(stop)
                all_stops.append(stop)
                timetable_data[stop] = []
            
            # Get bus assignment
            bus_id = run_to_bus.get(run.run_id, 'Unknown')
            
            # Store the calculated time for this stop
            timetable_data[stop].append({
                'run_id': run.run_id,
                'time': run.get_stop_time(i),
                'section': run.section,
                'bus_id': bus_id
            })
    
    # Keep runs in the original input order instead of sorting by run_id
    return render_template('schedule_modern.html', runs=runs, buses=buses, all_stops=all_stops, 
                          regulation=regulation, bus_breaks=bus_breaks, run_to_bus=run_to_bus,
                          min_layover_time=min_layover_time, min_break_extension=min_break_extension,
                          timetable_data=timetable_data)


@app.route('/srt-stats')
def srt_stats():
    """Display SRT database statistics with search functionality."""
    stats = srt_db.get_statistics()
    all_stations = srt_db.get_all_stations()
    
    # Get search parameters
    from_search = request.args.get('from_station', '').strip()
    to_search = request.args.get('to_station', '').strip()
    
    # Calculate station frequency (count of entries for each station)
    station_frequency = {}
    for entry in srt_db.data.values():
        from_station = entry.from_station
        to_station = entry.to_station
        station_frequency[from_station] = station_frequency.get(from_station, 0) + 1
        station_frequency[to_station] = station_frequency.get(to_station, 0) + 1
    
    # Get top 6 stations by frequency
    top_stations = sorted(station_frequency.items(), key=lambda x: x[1], reverse=True)[:6]
    top_stations_list = [station[0] for station in top_stations]
    
    # Get all travel times with optional filtering
    all_routes = []
    for entry in srt_db.data.values():
        # Apply search filters if provided
        if from_search and from_search.lower() not in entry.from_station.lower():
            continue
        if to_search and to_search.lower() not in entry.to_station.lower():
            continue
            
        all_routes.append({
            'from': entry.from_station,
            'to': entry.to_station,
            'duration': entry.duration_minutes,
            'updated': entry.last_updated
        })
    
    # Sort by from station, then by to station
    all_routes.sort(key=lambda x: (x['from'].lower(), x['to'].lower()))
    
    return render_template('srt_stats.html', 
                         stats=stats, 
                         all_stations=all_stations,
                         all_routes=all_routes,
                         from_search=from_search,
                         to_search=to_search,
                         top_stations=top_stations_list)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5620, debug=True)