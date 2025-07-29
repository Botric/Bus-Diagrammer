# This project provides a comprehensive web-based tool for scheduling buses onto inbound and outbound runs with advanced timetabling capabilities. It is designed to be self-hosted and operate within a single container (e.g. under Podman) to minimize resource usage. The scheduler assigns buses using configurable algorithms and takes into account daily driving limits, break requirements, and terminal-specific layover times defined by either EU (assimilated) rules or GB domestic drivers' hours rules.grammer

This project provides a simple web‑based tool for scheduling buses onto
inbound and outbound runs. It is designed to be self‑hosted and to
operate within a single container (e.g. under Podman) to minimise
resource usage. The scheduler assigns buses greedily so that the
minimum number of buses are used for a given set of runs and takes
into account the daily driving limits defined by either EU (assimilated)
rules or the GB domestic drivers’ hours rule.

## Features

### Core Scheduling
* **Two run sections** – Define both inbound and outbound runs with names, start/end times, stop sequences, and optional precise stop times
* **Regulation selection** – Choose between EU assimilated rules (max 9 hours/day, 45-min break after 4.5 hours) or GB domestic rules (max 10 hours/day, 30-min break after 5.5 hours)
* **Smart bus assignment** – Runs are assigned to minimize fleet size while respecting driving limits, break requirements, and terminal layover times
* **Terminal-specific layovers** – Configure different layover times for each terminal location
* **Travel time optimization** – Automatic SRT (Shortest Running Time) database tracks inter-terminal travel times

### Advanced Configuration
* **Configurable parameters** – Customize minimum layover times, break extensions, continuous driving limits, and terminal-specific settings
* **Alternating section preference** – Option to prefer alternating inbound/outbound runs to minimize deadheading
* **Break management** – Automatic calculation and display of mandatory driver breaks with customizable extensions
* **Skip configuration mode** – Quick deployment with sensible defaults

### Modern User Interface
* **Responsive design** – Modern glass-morphism interface that works on desktop and mobile
* **Collapsible sections** – Expandable/collapsible run entry sections and bus assignment displays
* **Color-coded visualization** – Each bus assigned a unique color maintained across all displays
* **Interactive timetables** – Separate inbound/outbound timetables with individual scrollbars
* **Real-time validation** – Dynamic form validation and error handling

### Data Management & Export
* **SRT Database** – Persistent database of inter-station travel times with automatic updates
* **Statistics page** – View travel time statistics, station frequencies, and database metrics
* **CSV Export** – Export detailed timetables with bus assignments and proper formatting
* **Print optimization** – Dedicated print styles for professional schedule printouts

### Enhanced Timetabling
* **Separated directional views** – Distinct inbound and outbound timetable sections
* **Bus assignment headers** – Run IDs displayed with corresponding bus numbers
* **Accurate stop times** – Support for precise stop times or calculated estimates
* **Professional formatting** – Compact, readable timetable layout with proper spacing

## Technology Stack

* **Python 3.11** with **Flask** for the web server and templating
* **Modern HTML5/CSS3** with glass-morphism design and responsive layout
* **Vanilla JavaScript** for dynamic interactions and CSV export functionality
* **JSON database** for persistent SRT (Shortest Running Time) data storage
* **Containerized deployment** with Podman/Docker support

## Quick Start

### Prerequisites
- Podman or Docker installed on your system
- Git (to clone the repository)

### Deployment Options

#### Option 1: Automated Deployment (Recommended)

**Windows (PowerShell):**
```powershell
# Clone the repository
git clone <repository-url>
cd Bus-Diagrammer

# Deploy with PowerShell script
.\deploy-podman.ps1
```

**Linux/macOS (Bash):**
```bash
# Clone the repository
git clone <repository-url>
cd Bus-Diagrammer

# Make script executable and deploy
chmod +x deploy-podman.sh
./deploy-podman.sh
```

#### Option 2: Manual Deployment

```bash
# Build the image
podman build -t bus-diagrammer:latest .

# Run the container
podman run -d \
    --name bus-diagrammer \
    -p 5620:5620 \
    --restart unless-stopped \
    -v "$(pwd)/srt_database.json:/home/appuser/app/srt_database.json:Z" \
    bus-diagrammer:latest
```

After deployment, open your browser to `http://localhost:5620` to use the application.

## Management Commands

### PowerShell (Windows)
```powershell
# View application status
.\deploy-podman.ps1 -Status

# View live logs
.\deploy-podman.ps1 -Logs

# Restart the application
.\deploy-podman.ps1 -Restart

# Stop the application
.\deploy-podman.ps1 -Stop
```

### Bash (Linux/macOS)
```bash
# View application status
./deploy-podman.sh --status

# View live logs
./deploy-podman.sh --logs

# Restart the application
./deploy-podman.sh --restart

# Stop the application
./deploy-podman.sh --stop
```

## Usage Guide

### Basic Workflow
1. **Enter Runs** – Add inbound and outbound runs with times and stops
2. **Configure Settings** – Choose regulation type and customize parameters (optional)
3. **Generate Schedule** – Let the system assign buses optimally
4. **Review Results** – View bus assignments, breaks, and detailed timetables
5. **Export Data** – Download CSV timetables or print schedules

### Advanced Features

#### SRT Database
The application automatically learns travel times between stations:
- Visit `/srt-stats` to view travel time statistics
- Search and filter travel times by station
- Database updates automatically from run data

#### Configuration Options
- **Minimum Layover Time**: Base time between runs (default: 15 minutes)
- **Break Extensions**: Additional time added to mandatory breaks
- **Continuous Driving Limits**: Override regulation defaults
- **Terminal-Specific Layovers**: Custom layover times per terminal
- **Section Alternation**: Prefer alternating inbound/outbound assignments

#### Export Options
- **CSV Export**: Detailed timetables with bus assignments
- **Print View**: Optimized layouts for professional printing
- **Automatic Formatting**: Three-row separation between inbound/outbound sections

## System Requirements

- **Memory**: 512MB RAM minimum
- **Storage**: 100MB disk space
- **CPU**: Single core sufficient
- **Network**: Port 5620 (configurable)
- **Container Runtime**: Podman 3.0+ or Docker 20.0+

## File Structure

```
Bus-Diagrammer/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container build configuration
├── deploy-podman.ps1     # Windows deployment script
├── deploy-podman.sh      # Linux/macOS deployment script
├── srt_database.json     # Persistent travel time database
├── templates/            # HTML templates
│   ├── index.html        # Main data entry form
│   ├── configure.html    # Configuration page
│   ├── schedule_modern.html # Results display
│   └── srt_stats.html    # Statistics page
└── static/              # CSS and assets
    └── css/
        └── modern-styles.css
```

## Development Considerations

### Current Implementation
- **Production Ready** – Comprehensive error handling and validation
- **Scalable Design** – Efficient algorithms handle large datasets
- **User-Friendly** – Intuitive interface with helpful guidance
- **Maintainable** – Clean code structure with detailed documentation

### Potential Extensions
- **Multi-day Scheduling** – Support for schedules spanning multiple days
- **Driver Management** – Individual driver assignments and tracking
- **Vehicle Types** – Different bus types with specific route restrictions
- **Real-time Updates** – Live schedule modifications and notifications
- **API Integration** – REST API for external system integration
- **Database Backend** – PostgreSQL/MySQL support for enterprise use

### Performance Notes
- **Memory Usage** – Optimized for minimal resource consumption
- **Response Times** – Sub-second scheduling for typical route sizes
- **Concurrent Users** – Single-user design, multi-user requires load balancing
- **Data Persistence** – SRT database automatically saved, runs are session-based

## Troubleshooting

### Common Issues

**Container Won't Start**
```bash
# Check container logs
podman logs bus-diagrammer

# Verify port availability
netstat -tulpn | grep 5620
```

**Permission Denied (Linux)**
```bash
# Fix script permissions
chmod +x deploy-podman.sh

# Check SELinux context for volume mounts
ls -Z srt_database.json
```

**Database Not Persisting**
```bash
# Ensure database file exists and has correct permissions
touch srt_database.json
chmod 644 srt_database.json
```

### Getting Help
- Check the application logs using the management scripts
- Verify all prerequisites are installed correctly
- Ensure no other services are using port 5620

## License

This project is provided under the MIT License. See `LICENSE` for details.

## Version History

- **v2.0** – Complete UI overhaul, advanced timetabling, export functionality
- **v1.5** – SRT database, configuration options, break management
- **v1.0** – Basic scheduling with simple timetable display