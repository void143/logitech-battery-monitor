# Logitech Battery Monitor

A lightweight Windows system-tray application that shows your Logitech mouse battery level at all times — no Logitech app required.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **Live battery percentage** in the system tray icon with colour coding
  - 🟢 Green — above 30%
  - 🟡 Yellow — 20–30%
  - 🟠 Orange — 10–20%
  - 🔴 Red — 10% and below
- **Hover tooltip** showing device name and exact percentage
- **Toast notifications** at ≤20%, ≤10%, and ≤5% with escalating urgency
- **No Logitech software dependency** — reads directly from the device via Bluetooth
- **Automatic refresh** every 5 minutes (configurable)
- **Start with Windows** toggle in the right-click menu

---

## Supported Devices

Tested with:
- Logitech MX Anywhere 2

Should work with any Logitech Bluetooth mouse that exposes the standard BLE Battery Service (UUID `0x180F`). More devices will be added based on user feedback.

---

## Requirements

- Windows 10 or 11
- Python 3.10+
- Logitech mouse paired via Bluetooth

---

## Installation

1. **Clone or download** this repository:
   ```
   git clone https://github.com/void143/logitech-battery-monitor.git
   cd logitech-battery-monitor
   ```

2. **Install dependencies** — double-click `install.bat` or run:
   ```
   pip install -r requirements.txt
   ```

3. **Launch** — double-click `start.bat`

The tray icon appears within a few seconds. The first battery reading takes up to 15 seconds while the app locates your device.

> **Tip:** If the icon doesn't appear on the taskbar, check the notification area overflow (the `^` arrow on the right side of the taskbar).

---

## Usage

Right-click the tray icon for options:

| Menu item | Action |
|---|---|
| Refresh Now | Read battery level immediately |
| Rescan Device | Clear cached device address and scan again |
| Start with Windows | Toggle autostart via the Windows registry |
| Exit | Quit the application |

---

## Configuration

Edit the constants at the top of `monitor.py`:

| Constant | Default | Description |
|---|---|---|
| `CHECK_INTERVAL` | `300` | Seconds between automatic refreshes |
| `ALERT_LEVELS` | `[20, 10, 5]` | Battery % thresholds that trigger notifications |
| `DEVICE_KEYWORDS` | `["MX Anywhere", "MX Master", "Logitech"]` | Names used to identify your device |

---

## How It Works

The app uses two methods to read battery level, tried in order:

1. **BLE GATT Battery Service** (primary) — connects directly to the mouse over Bluetooth LE and reads the standard Battery Level characteristic (`0x2A19`). Works when the mouse is advertising as a BLE peripheral.

2. **Windows Device Information API** (fallback) — queries the Windows device property store via PowerShell. Works when the mouse is connected via Bluetooth Classic or the Bolt USB receiver.

Config and logs are stored in `%USERPROFILE%\.logitech_battery_monitor\`.

---

## Troubleshooting

**Icon doesn't appear**
- Check the taskbar overflow area (`^` arrow near the clock)
- Make sure Python is on your PATH: `python --version` in a terminal

**Always shows Unknown**
- Confirm your mouse is paired via Bluetooth (not just the USB receiver)
- Try right-click → Rescan Device

**Battery jumps in large steps (e.g. 25%, 50%, 75%)**
- This is normal — Logitech firmware reports in coarse increments

---

## License

MIT — see [LICENSE](LICENSE)

---

## Contributing

Pull requests welcome. If your Logitech device isn't detected, open an issue with the device name as shown in Windows Bluetooth settings.
