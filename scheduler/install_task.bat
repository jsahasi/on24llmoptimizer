@echo off
REM Creates a Windows Task Scheduler task to run the benchmark weekly (Monday 6:00 AM)
REM Run this script as Administrator

schtasks /create ^
  /tn "ON24_GEO_Benchmark" ^
  /tr "python C:\Users\jayesh.sahasi\on24llmoptimizer\run_benchmark.py" ^
  /sc weekly ^
  /d MON ^
  /st 06:00 ^
  /ru "%USERNAME%" ^
  /rl HIGHEST ^
  /f

echo Task created (runs every Monday at 6:00 AM).
echo Verify with: schtasks /query /tn "ON24_GEO_Benchmark" /v
pause
