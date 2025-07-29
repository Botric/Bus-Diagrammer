# Bus Scheduler

This project provides a simple web‑based tool for scheduling buses onto
inbound and outbound runs. It is designed to be self‑hosted and to
operate within a single container (e.g. under Podman) to minimise
resource usage. The scheduler assigns buses greedily so that the
minimum number of buses are used for a given set of runs and takes
into account the daily driving limits defined by either EU (assimilated)
rules or the GB domestic drivers’ hours rules【830846819082181†L114-L122】【344526805669237†L186-L192】.

## Features

* **Two run sections** – You can define both inbound and outbound runs.
  Each run includes a name, start time, end time and an optional list
  of stops.
* **Regulation selection** – Choose between the assimilated (EU) rules
  (maximum 9 driving hours per day with a 45‑minute break after
  4.5 hours)【830846819082181†L114-L135】 or the GB domestic rules (maximum 10 driving hours per day with
  breaks after 5.5 hours)【344526805669237†L186-L208】. The current implementation only enforces
  the total daily driving limit.
* **Greedy bus assignment** – Runs are sorted by start time and assigned
  to the first available bus that can accommodate them without
  exceeding the daily driving limit. If no bus is available, a new
  one is created.
* **Timetable view** – After scheduling, the tool displays a table
  listing all stops (rows) against all runs (columns). Each cell shows
  the stop order number within a run.
* **Bus roster** – A simple roster lists which runs have been assigned
  to each bus along with their time windows.

## Technology stack

* **Python 3.11** with **Flask** for the web server and templating.
* HTML, CSS and vanilla JavaScript for the front end. Runs can be
  added and removed dynamically without reloading the page.
* A single **Dockerfile** (or Podman container) builds and runs the
  application. No separate database container is required – all data
  lives in memory for the duration of the session.

## Running locally

1. **Install dependencies**: Create a virtual environment, then run

   ```bash
   pip install -r requirements.txt
   ```

2. **Start the application**:

   ```bash
   python app.py
   ```

   By default the Flask development server listens on `http://0.0.0.0:5000`.

3. Open your browser to `http://localhost:5000` and begin entering
   inbound and outbound runs.

## Building and running with Podman/Docker

To build the image (e.g. with Podman):

```bash
podman build -t bus-scheduler .
```

Then run it:

```bash
podman run --rm -p 5000:5000 bus-scheduler
```

Navigate to `http://localhost:5000` in your browser to use the tool.

## Development considerations

* **Time estimate** – Developing this minimal scheduler with a basic
  front end and greedy allocation algorithm would take a competent
  developer roughly **2–3 days**, including containerisation, basic
  testing and documentation. Implementing robust validations, a richer
  user interface (e.g. drag‑and‑drop editing, import/export of Excel
  files) or more sophisticated scheduling (taking account of
  break/rest periods, driver rosters or vehicle types) would add
  significant complexity and could extend the timeline to several
  weeks.
* **Extensibility** – The current design deliberately keeps the data
  model simple. If you wish to support additional constraints (such as
  mandatory breaks after 4.5 hours of driving under EU rules【830846819082181†L124-L135】 or
  5.5 hours under GB domestic rules【344526805669237†L195-L207】) or to record which bus types are
  eligible for particular runs, the scheduling algorithm and form
  schema will need to evolve accordingly.

## Licence

This project is provided under the MIT Licence. See `LICENSE` for
details.