# Bus Diagrammer - Quick Deployment Guide

## Ready to Deploy? 🚀

Your Bus Diagrammer application is now ready for production deployment with Podman containers!

## What's New in v2.0?

✅ **Modern UI** - Glass-morphism design with responsive layout  
✅ **Advanced Timetabling** - Separate inbound/outbound displays  
✅ **Export Functionality** - CSV export with bus assignments  
✅ **Individual Scrollbars** - Better navigation for large timetables  
✅ **SRT Database** - Automatic travel time learning and optimization  
✅ **Production Deployment** - Automated Podman container scripts  

## Quick Deploy Commands

### Windows (PowerShell)
```powershell
# Stop development server if running
# Deploy to production
.\deploy-podman.ps1

# Check status
.\deploy-podman.ps1 -Status

# View logs
.\deploy-podman.ps1 -Logs
```

### Linux/macOS (Bash)
```bash
# Stop development server if running
# Deploy to production
./deploy-podman.sh

# Check status
./deploy-podman.sh --status

# View logs
./deploy-podman.sh --logs
```

## What the Deployment Does

1. **Builds Container Image** - Creates optimized production image
2. **Configures Persistence** - Mounts SRT database for data persistence
3. **Sets Up Networking** - Exposes application on port 5620
4. **Enables Auto-Restart** - Container restarts automatically on failure
5. **Runs in Background** - Detached mode for production use

## Accessing Your Application

After successful deployment:
- **URL**: http://localhost:5620
- **Container Name**: bus-diagrammer
- **Persistent Data**: srt_database.json (automatically maintained)

## Production Features Available

- ✅ All new UI enhancements
- ✅ CSV export with bus assignments
- ✅ Individual scrollbars for timetables  
- ✅ SRT database statistics at `/srt-stats`
- ✅ Professional print layouts
- ✅ Responsive mobile interface

## Need Help?

Check the full README.md for:
- Complete feature documentation
- Troubleshooting guide
- Advanced configuration options
- System requirements

Your application is production-ready! 🎉
