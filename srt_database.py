"""Simple SRT Database implementation."""

import json
import os
from datetime import datetime
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
        from datetime import timedelta
        
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
