#!/usr/bin/env python3
"""
Software 'unplug/replug' for the stuck CH340 reader port (Windows error 31).
Disables then re-enables the CH340 device so you don't have to physically
unplug the USB. MUST be run from an ADMIN PowerShell/terminal.

Usage:  python reset_port.py
"""
import subprocess, sys

PS = (
    "$ErrorActionPreference='Stop';"
    "$d = Get-PnpDevice -Class Ports -PresentOnly | "
    "  Where-Object { $_.FriendlyName -match 'CH340' };"
    "if (-not $d) { Write-Output 'NODEV'; exit 0 }"
    "foreach ($dev in $d) {"
    "  Write-Output ('Resetting: ' + $dev.FriendlyName);"
    "  try {"
    "    Disable-PnpDevice -InstanceId $dev.InstanceId -Confirm:$false;"
    "    Start-Sleep -Milliseconds 700;"
    "    Enable-PnpDevice  -InstanceId $dev.InstanceId -Confirm:$false;"
    "  } catch { Write-Output 'DENIED'; exit 1 }"
    "}"
    "Write-Output 'CYCLED'"
)

r = subprocess.run(
    ["powershell", "-NoProfile", "-NonInteractive", "-Command", PS],
    capture_output=True, text=True,
)
out = (r.stdout or "") + (r.stderr or "")
print(out.strip())

if "CYCLED" in out:
    print("\nDone. The CH340 was reset -- you can run scan_input.py now.")
elif "DENIED" in out or "denied" in out.lower() or "AccessDenied" in out:
    print("\nFAILED: run this from an ADMIN terminal (right-click PowerShell "
          "-> Run as administrator), or just unplug/replug the USB.")
    sys.exit(1)
elif "NODEV" in out:
    print("\nNo CH340 device found -- is the reader plugged in?")
    sys.exit(1)
