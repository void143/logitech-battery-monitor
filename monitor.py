"""
Logitech Mouse Battery Monitor
Windows system-tray app — reads battery via BLE GATT or Windows Device API.
"""
from __future__ import annotations

import asyncio
import ctypes
import json
import logging
import os
import re
import subprocess
import sys
import threading
import winreg
from pathlib import Path

import pystray
from bleak import BleakClient, BleakScanner
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
APP_VERSION    = "1.0.2"
CHECK_INTERVAL = 5 * 60          # seconds between automatic refreshes
ALERT_LEVELS   = [20, 10, 5]     # thresholds for toast notifications (desc order)
BLE_SCAN_TIMEOUT  = 15.0         # seconds for BLE device discovery
BLE_CONN_TIMEOUT  = 15.0         # seconds for BLE connection
DEVICE_KEYWORDS   = ["MX Anywhere", "MX Master", "Logitech"]

GATT_BATTERY_SERVICE = "0000180f-0000-1000-8000-00805f9b34fb"
GATT_BATTERY_CHAR    = "00002a19-0000-1000-8000-00805f9b34fb"

CONFIG_DIR  = Path(os.environ["USERPROFILE"]) / ".logitech_battery_monitor"
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_FILE    = CONFIG_DIR / "monitor.log"

REGISTRY_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REGISTRY_VALUE   = "LogitechBatteryMonitor"

APP_NAME = "Logitech Battery Monitor"

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Icon generation
# ---------------------------------------------------------------------------
def make_icon(battery: int | None) -> Image.Image:
    """Return a 64×64 RGBA PIL image representing the battery level."""
    W, H = 64, 64
    img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Colour coding
    if battery is None:
        body_colour  = (160, 160, 160, 255)   # grey
        fill_colour  = (120, 120, 120, 255)
    elif battery > 30:
        body_colour  = (60, 179, 113, 255)    # green
        fill_colour  = (34, 139, 34, 255)
    elif battery > 20:
        body_colour  = (255, 215, 0, 255)     # yellow
        fill_colour  = (218, 165, 32, 255)
    elif battery > 10:
        body_colour  = (255, 140, 0, 255)     # orange
        fill_colour  = (210, 105, 30, 255)
    else:
        body_colour  = (220, 50, 47, 255)     # red
        fill_colour  = (178, 34, 34, 255)

    # Battery body dimensions
    margin   = 4
    nub_w    = 6
    nub_h    = 16
    body_x0  = margin
    body_y0  = (H - 36) // 2
    body_x1  = W - margin - nub_w - 2
    body_y1  = body_y0 + 36

    # Outline
    outline_w = 3
    draw.rounded_rectangle(
        [body_x0, body_y0, body_x1, body_y1],
        radius=4,
        outline=body_colour,
        width=outline_w,
    )

    # Terminal nub
    nub_x0 = body_x1 + 2
    nub_x1 = nub_x0 + nub_w
    nub_y0 = body_y0 + (body_y1 - body_y0 - nub_h) // 2
    nub_y1 = nub_y0 + nub_h
    draw.rounded_rectangle(
        [nub_x0, nub_y0, nub_x1, nub_y1],
        radius=2,
        fill=body_colour,
    )

    # Fill bar (inside body)
    inner_margin = outline_w + 2
    inner_x0 = body_x0 + inner_margin
    inner_y0 = body_y0 + inner_margin
    inner_x1 = body_x1 - inner_margin
    inner_y1 = body_y1 - inner_margin
    inner_w  = inner_x1 - inner_x0

    if battery is not None and battery > 0:
        fill_w = max(2, int(inner_w * battery / 100))
        draw.rounded_rectangle(
            [inner_x0, inner_y0, inner_x0 + fill_w, inner_y1],
            radius=2,
            fill=fill_colour,
        )

    # Percentage text
    label = "?" if battery is None else f"{battery}%"
    try:
        font = ImageFont.truetype("arialbd.ttf", 14)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    cx = (body_x0 + body_x1) // 2
    cy = (body_y0 + body_y1) // 2
    draw.text(
        (cx - tw // 2, cy - th // 2),
        label,
        font=font,
        fill=(255, 255, 255, 230),
    )

    return img


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
def send_notification(title: str, body: str, level: str = "warning") -> None:
    """Fire a Windows toast notification via PowerShell (no console window)."""
    icon_map = {
        "info":    "SystemIcons.Information",
        "warning": "SystemIcons.Warning",
        "error":   "SystemIcons.Error",
    }
    icon_expr = icon_map.get(level, "SystemIcons.Warning")

    ps = f"""
Add-Type -AssemblyName System.Windows.Forms
$ni = New-Object System.Windows.Forms.NotifyIcon
$ni.Icon = [System.Drawing.SystemIcons]::{icon_expr.split('.')[-1]}
$ni.Visible = $true
$ni.ShowBalloonTip(8000, '{title}', '{body}', [System.Windows.Forms.ToolTipIcon]::{level.capitalize()})
Start-Sleep -Milliseconds 9000
$ni.Dispose()
"""
    try:
        subprocess.Popen(
            ["powershell", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as exc:
        log.warning("Notification failed: %s", exc)


# ---------------------------------------------------------------------------
# Config persistence
# ---------------------------------------------------------------------------
def load_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(cfg: dict) -> None:
    try:
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception as exc:
        log.warning("Could not save config: %s", exc)


# ---------------------------------------------------------------------------
# BLE reading
# ---------------------------------------------------------------------------
def _is_logitech_device(name: str | None) -> bool:
    if not name:
        return False
    return any(kw.lower() in name.lower() for kw in DEVICE_KEYWORDS)


async def ble_find_device() -> tuple[str, str] | None:
    """Scan for a Logitech BLE device and return (address, name)."""
    log.info("BLE scan started (timeout=%.0fs)…", BLE_SCAN_TIMEOUT)

    def match(device, _adv):
        return _is_logitech_device(device.name)

    device = await BleakScanner.find_device_by_filter(match, timeout=BLE_SCAN_TIMEOUT)
    if device:
        log.info("Found device: %s [%s]", device.name, device.address)
        return device.address, device.name or "Logitech Mouse"
    log.warning("No Logitech BLE device found during scan.")
    return None


async def ble_read_battery(address: str) -> int | None:
    """Connect to device at *address* and read the Battery Level characteristic."""
    try:
        async with BleakClient(address, timeout=BLE_CONN_TIMEOUT) as client:
            # Walk services looking for Battery Service
            for svc in client.services:
                if "180f" in svc.uuid.lower():
                    for char in svc.characteristics:
                        if "2a19" in char.uuid.lower():
                            data = await client.read_gatt_char(char.uuid)
                            level = data[0]
                            log.info("BLE battery: %d%%", level)
                            return level
            log.warning("Battery Service not found on device %s", address)
    except Exception as exc:
        log.warning("BLE read failed (%s): %s", address, exc)
    return None


# ---------------------------------------------------------------------------
# Windows Device Information API fallback (PowerShell)
# ---------------------------------------------------------------------------
_PS_WINDEV = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Devices.Enumeration.DeviceInformation,Windows.Devices.Enumeration,ContentType=WindowsRuntime]
$aqsFilter = 'System.Devices.InterfaceClassGuid:="{0000180F-0000-1000-8000-00805F9B34FB}"'
$props = [System.Collections.Generic.List[string]]@("System.Devices.BatteryPlusCharging","System.ItemNameDisplay")
$asyncOp = [Windows.Devices.Enumeration.DeviceInformation]::FindAllAsync($aqsFilter, $props)
$task    = [System.WindowsRuntimeSystemExtensions]::AsTask($asyncOp)
$null    = $task.Wait(10000)
foreach ($dev in $task.Result) {
    $name  = $dev.Properties["System.ItemNameDisplay"]
    $level = $dev.Properties["System.Devices.BatteryPlusCharging"]
    if ($name -and $level -ne $null) {
        Write-Output "$name|$level"
    }
}
"""

_PS_SIMPLE = r"""
$devices = Get-PnpDevice -Class Bluetooth -Status OK | Where-Object { $_.FriendlyName -match 'MX|Logitech' }
foreach ($d in $devices) {
    $props = Get-PnpDeviceProperty -InstanceId $d.InstanceId -KeyName '{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2' -ErrorAction SilentlyContinue
    if ($props -and $props.Data -ne $null) {
        Write-Output "$($d.FriendlyName)|$($props.Data)"
    }
}
"""


def windev_read_battery() -> int | None:
    """Try Windows Device Information API via PowerShell to get battery level."""
    for script in [_PS_WINDEV, _PS_SIMPLE]:
        try:
            result = subprocess.run(
                ["powershell", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", script],
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                if "|" in line:
                    name, level_str = line.rsplit("|", 1)
                    if _is_logitech_device(name):
                        m = re.search(r"\d+", level_str)
                        if m:
                            level = int(m.group())
                            if 0 <= level <= 100:
                                log.info("WinDev battery: %d%% (%s)", level, name)
                                return level
        except Exception as exc:
            log.debug("WinDev script failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Registry helpers (Start with Windows)
# ---------------------------------------------------------------------------
def _get_startup_entry() -> str | None:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_RUN_KEY)
        val, _ = winreg.QueryValueEx(key, REGISTRY_VALUE)
        winreg.CloseKey(key)
        return val
    except FileNotFoundError:
        return None


def _set_startup_entry(enable: bool) -> None:
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, REGISTRY_RUN_KEY,
        access=winreg.KEY_SET_VALUE,
    )
    if enable:
        if getattr(sys, "frozen", False):
            # Running as a PyInstaller-bundled exe
            cmd = f'"{sys.executable}"'
        else:
            pythonw = Path(sys.executable).with_name("pythonw.exe")
            script  = Path(__file__).resolve()
            cmd = f'"{pythonw}" "{script}"'
        winreg.SetValueEx(key, REGISTRY_VALUE, 0, winreg.REG_SZ, cmd)
        log.info("Added to startup registry.")
    else:
        try:
            winreg.DeleteValue(key, REGISTRY_VALUE)
            log.info("Removed from startup registry.")
        except FileNotFoundError:
            pass
    winreg.CloseKey(key)


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------
class MouseBatteryMonitor:
    def __init__(self) -> None:
        self._cfg:         dict       = load_config()
        self._battery:     int | None = None
        self._device_name: str        = self._cfg.get("device_name", "Logitech Mouse")
        self._address:     str | None = self._cfg.get("address")
        self._alerted:     set[int]   = set()

        self._loop:   asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None          = None
        self.icon:    pystray.Icon | None              = None

    # ------------------------------------------------------------------
    # Icon / tooltip helpers
    # ------------------------------------------------------------------
    def _update_icon(self) -> None:
        if self.icon is None:
            return
        self.icon.icon = make_icon(self._battery)
        if self._battery is None:
            status = "Unknown"
        elif self._battery > 30:
            status = "Good"
        elif self._battery > 20:
            status = "OK"
        elif self._battery > 10:
            status = "Low"
        else:
            status = "Critical"
        self.icon.title = (
            f"{self._device_name}\n"
            f"Battery: {self._battery}% ({status})\n"
            f"Logitech Battery Monitor"
        ) if self._battery is not None else (
            f"{self._device_name}\nBattery: Unknown\nLogitech Battery Monitor"
        )

    # ------------------------------------------------------------------
    # Alert logic
    # ------------------------------------------------------------------
    def _handle_alerts(self, level: int) -> None:
        # Reset alerted thresholds if battery recovered
        recovered = {t for t in self._alerted if level > t}
        self._alerted -= recovered

        for threshold in sorted(ALERT_LEVELS, reverse=True):
            if level <= threshold and threshold not in self._alerted:
                self._alerted.add(threshold)
                if threshold <= 5:
                    sev, icon_level = "CRITICAL", "error"
                elif threshold <= 10:
                    sev, icon_level = "Very Low", "warning"
                else:
                    sev, icon_level = "Low", "warning"
                send_notification(
                    f"{self._device_name} Battery {sev}",
                    f"Battery is at {level}%. Please charge soon.",
                    icon_level,
                )
                break   # one notification per refresh

    # ------------------------------------------------------------------
    # Battery reading pipeline
    # ------------------------------------------------------------------
    async def _read_battery_async(self) -> int | None:
        # 1. Try BLE with cached address
        if self._address:
            lvl = await ble_read_battery(self._address)
            if lvl is not None:
                return lvl
            log.info("Cached address failed; will rescan.")
            self._address = None

        # 2. BLE scan
        result = await ble_find_device()
        if result:
            self._address, self._device_name = result
            self._cfg["address"]     = self._address
            self._cfg["device_name"] = self._device_name
            save_config(self._cfg)
            lvl = await ble_read_battery(self._address)
            if lvl is not None:
                return lvl

        # 3. Windows Device API fallback
        log.info("Trying Windows Device API fallback…")
        lvl = await asyncio.get_event_loop().run_in_executor(None, windev_read_battery)
        return lvl

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------
    async def _refresh(self) -> None:
        log.info("Refreshing battery level…")
        try:
            level = await self._read_battery_async()
            self._battery = level
            if level is not None:
                self._handle_alerts(level)
        except Exception as exc:
            log.error("Unexpected error during refresh: %s", exc)
        self._update_icon()

    # ------------------------------------------------------------------
    # Background monitor loop
    # ------------------------------------------------------------------
    def _monitor_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def _periodic():
            while True:
                await self._refresh()
                await asyncio.sleep(CHECK_INTERVAL)

        self._loop.run_until_complete(_periodic())

    # ------------------------------------------------------------------
    # Menu callbacks
    # ------------------------------------------------------------------
    def _on_refresh(self, icon, item) -> None:  # noqa: ARG002
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._refresh(), self._loop)

    def _on_rescan(self, icon, item) -> None:  # noqa: ARG002
        self._address = None
        self._cfg.pop("address", None)
        save_config(self._cfg)
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._refresh(), self._loop)

    def _on_toggle_startup(self, icon, item) -> None:  # noqa: ARG002
        current = _get_startup_entry() is not None
        _set_startup_entry(not current)

    def _startup_checked(self, item) -> bool:  # noqa: ARG002
        return _get_startup_entry() is not None

    def _on_exit(self, icon, item) -> None:  # noqa: ARG002
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        icon.stop()

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def run(self) -> None:
        # Start background thread
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

        # Build tray menu
        menu = pystray.Menu(
            pystray.MenuItem("Refresh Now",         self._on_refresh),
            pystray.MenuItem("Rescan Device",       self._on_rescan),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Start with Windows",
                self._on_toggle_startup,
                checked=self._startup_checked,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit",                self._on_exit),
        )

        self.icon = pystray.Icon(
            APP_NAME,
            make_icon(None),
            APP_NAME,
            menu,
        )
        self._update_icon()
        self.icon.run()


# ---------------------------------------------------------------------------
# Single-instance guard
# ---------------------------------------------------------------------------
_MUTEX_HANDLE = None   # keep reference so the handle stays open


def _acquire_single_instance() -> bool:
    """Create a named Windows mutex.  Returns False if another instance owns it."""
    global _MUTEX_HANDLE
    ERROR_ALREADY_EXISTS = 183
    handle = ctypes.windll.kernel32.CreateMutexW(None, True, "LogitechBatteryMonitor_SingleInstance")
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
        return False
    _MUTEX_HANDLE = handle   # keep alive for the lifetime of the process
    return True


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if not _acquire_single_instance():
        # Another instance is already running — bail out silently.
        sys.exit(0)
    log.info("Starting %s", APP_NAME)
    app = MouseBatteryMonitor()
    app.run()
