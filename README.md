# Logitech Battery Monitor

A lightweight Windows system-tray app that always shows your Logitech mouse battery level — no Logitech software required.

![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-1.0.2-orange)

---

## Download & Install

**No Python or technical knowledge required.**

1. Go to the [**Releases**](../../releases/latest) page
2. Download `LogitechBatteryMonitor-1.0.2-x64.msi`
3. Double-click the file and follow the installer
4. The app starts automatically and appears in your system tray (bottom-right corner of the taskbar)

> **Can't see the icon?** Click the **`^`** arrow on the right side of your taskbar to reveal hidden icons. You can drag the battery icon out to keep it always visible.

---

## Features

- **Live battery percentage** always visible in the system tray
- **Colour-coded icon** so you can see the status at a glance:
  - 🟢 Green — above 30%
  - 🟡 Yellow — 20–30%
  - 🟠 Orange — 10–20%
  - 🔴 Red — 10% and below
- **Hover tooltip** — shows device name and exact percentage
- **Pop-up alerts** when battery reaches 20%, 10%, and 5%
- **No Logitech software needed** — reads the battery directly from the mouse over Bluetooth
- Checks automatically every 5 minutes
- Right-click the icon to refresh immediately or enable **Start with Windows**

---

## System Requirements

- Windows 10 or Windows 11 (64-bit)
- A Logitech mouse paired via Bluetooth
- That's it — no Python, no drivers, no extra software

---

## Supported Devices

Tested with:
- Logitech MX Anywhere 2

Should work with any Logitech Bluetooth mouse. If your device isn't detected, open an issue and include the device name shown in Windows Bluetooth settings.

---

## Troubleshooting

**The icon doesn't appear after installing**
- Look for the hidden icons arrow (`^`) near the clock on your taskbar
- If still missing, right-click the taskbar → Task Manager → check if `LogitechBatteryMonitor.exe` is running under Background processes

**Always shows "Unknown"**
- Make sure your mouse is paired via Bluetooth (Settings → Bluetooth & devices)
- Right-click the tray icon → **Rescan Device**

**Battery jumps in big steps (e.g. 25% → 50%)**
- This is normal — Logitech firmware reports in coarse steps

---

## For Developers

If you want to run from source or contribute:

1. Install Python 3.10+ from [python.org](https://www.python.org)
2. Clone this repo:
   ```
   git clone https://github.com/void143/logitech-battery-monitor.git
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run directly (no install needed):
   ```
   pythonw monitor.py
   ```

To build the MSI locally (requires .NET SDK):
```
powershell -ExecutionPolicy Bypass -File installer\build_msi.ps1
```

The output MSI lands in `dist\`.

---

## License

MIT — see [LICENSE](LICENSE)

---

## Contributing

Pull requests are welcome. If your Logitech device isn't detected, please open an issue.
