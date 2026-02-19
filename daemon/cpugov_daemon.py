#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# cpugov-daemon — D-Bus system service for CPU governor control
"""
A lightweight D-Bus system service that provides authorized access
to CPU frequency scaling governor settings via Polkit.

Bus name: io.github.serverket.cpugov
Object:   /io/github/serverket/cpugov
Interface: io.github.serverket.cpugov
"""

import json
import os
import glob
import signal
import sys
from pathlib import Path

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

BUS_NAME = "io.github.serverket.cpugov"
OBJECT_PATH = "/io/github/serverket/cpugov"
INTERFACE_NAME = "io.github.serverket.cpugov"

POLKIT_ACTION_SET = "io.github.serverket.cpugov.set-governor"

SYSFS_CPU_BASE = "/sys/devices/system/cpu"
GOVERNOR_PATH = "cpufreq/scaling_governor"
AVAIL_GOVERNORS_PATH = "cpufreq/scaling_available_governors"
CUR_FREQ_PATH = "cpufreq/scaling_cur_freq"
MIN_FREQ_PATH = "cpufreq/cpuinfo_min_freq"
MAX_FREQ_PATH = "cpufreq/cpuinfo_max_freq"
CPU_MODEL_PATH = "/proc/cpuinfo"
CONFIG_PATH = "/var/lib/cpugov/config.json"


class CPUGovDaemon(dbus.service.Object):
    """D-Bus system service for CPU governor management."""

    def __init__(self, bus):
        bus_name = dbus.service.BusName(BUS_NAME, bus=bus)
        super().__init__(bus_name, OBJECT_PATH)
        self._bus = bus
        # Restore saved governor on startup
        self._restore_governor()

    # ── Helper methods ────────────────────────────────────────────

    @staticmethod
    def _get_cpu_dirs():
        """Return sorted list of cpu directories that have cpufreq."""
        pattern = os.path.join(SYSFS_CPU_BASE, "cpu[0-9]*")
        dirs = sorted(glob.glob(pattern),
                      key=lambda d: int(os.path.basename(d)[3:]))
        return [d for d in dirs
                if os.path.exists(os.path.join(d, GOVERNOR_PATH))]

    @staticmethod
    def _read_sysfs(path):
        """Read a sysfs file and return stripped content."""
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except (IOError, OSError):
            return ""

    @staticmethod
    def _write_sysfs(path, value):
        """Write a value to a sysfs file."""
        with open(path, "w") as f:
            f.write(value)

    def _check_polkit_auth(self, sender, action_id):
        """Check Polkit authorization for the calling process."""
        proxy = self._bus.get_object(
            "org.freedesktop.PolicyKit1",
            "/org/freedesktop/PolicyKit1/Authority"
        )
        authority = dbus.Interface(
            proxy,
            "org.freedesktop.PolicyKit1.Authority"
        )

        subject = (
            "system-bus-name",
            {"name": dbus.String(sender, variant_level=1)}
        )

        result = authority.CheckAuthorization(
            subject,
            action_id,
            {},  # details
            dbus.UInt32(1),  # AllowUserInteraction
            "",  # cancellation_id
        )

        is_authorized = result[0]
        if not is_authorized:
            raise dbus.exceptions.DBusException(
                f"Not authorized for action: {action_id}",
                name="org.freedesktop.PolicyKit1.Error.NotAuthorized"
            )

    def _get_cpu_model(self):
        """Read CPU model from /proc/cpuinfo."""
        try:
            with open(CPU_MODEL_PATH, "r") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except (IOError, OSError):
            pass
        return "Unknown"

    def _save_governor(self, governor):
        """Save the governor choice to config file for persistence."""
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            config = {"governor": governor}
            with open(CONFIG_PATH, "w") as f:
                json.dump(config, f, indent=2)
                f.write("\n")
            print(f"cpugov-daemon: saved governor '{governor}' to {CONFIG_PATH}",
                  file=sys.stderr)
        except (IOError, OSError) as e:
            print(f"cpugov-daemon: failed to save config: {e}",
                  file=sys.stderr)

    def _load_saved_governor(self):
        """Load the saved governor from /etc/cpugov.conf."""
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
            return config.get("governor")
        except (IOError, OSError, json.JSONDecodeError):
            return None

    def _restore_governor(self):
        """Restore the saved governor on daemon startup."""
        saved = self._load_saved_governor()
        if not saved:
            return

        # Validate it's still available
        cpu_dirs = self._get_cpu_dirs()
        if not cpu_dirs:
            return

        path = os.path.join(cpu_dirs[0], AVAIL_GOVERNORS_PATH)
        available = self._read_sysfs(path).split()
        if saved not in available:
            print(f"cpugov-daemon: saved governor '{saved}' no longer available, skipping",
                  file=sys.stderr)
            return

        # Apply to all CPUs
        for cpu_dir in cpu_dirs:
            try:
                self._write_sysfs(
                    os.path.join(cpu_dir, GOVERNOR_PATH), saved
                )
            except (IOError, OSError) as e:
                print(f"cpugov-daemon: failed to restore governor on {cpu_dir}: {e}",
                      file=sys.stderr)

        print(f"cpugov-daemon: restored governor '{saved}' from {CONFIG_PATH}",
              file=sys.stderr)

    # ── D-Bus methods ─────────────────────────────────────────────

    @dbus.service.method(
        INTERFACE_NAME,
        in_signature="",
        out_signature="s",
        sender_keyword="sender"
    )
    def GetGovernor(self, sender=None):
        """Get the current governor for cpu0."""
        cpu_dirs = self._get_cpu_dirs()
        if not cpu_dirs:
            return "unknown"
        path = os.path.join(cpu_dirs[0], GOVERNOR_PATH)
        return self._read_sysfs(path)

    @dbus.service.method(
        INTERFACE_NAME,
        in_signature="",
        out_signature="as",
        sender_keyword="sender"
    )
    def GetAvailableGovernors(self, sender=None):
        """Get list of available governors."""
        cpu_dirs = self._get_cpu_dirs()
        if not cpu_dirs:
            return dbus.Array([], signature="s")
        path = os.path.join(cpu_dirs[0], AVAIL_GOVERNORS_PATH)
        governors = self._read_sysfs(path).split()
        return dbus.Array(governors, signature="s")

    @dbus.service.method(
        INTERFACE_NAME,
        in_signature="s",
        out_signature="b",
        sender_keyword="sender"
    )
    def SetGovernor(self, governor, sender=None):
        """Set the governor for all CPUs. Requires Polkit authorization."""
        # Validate governor name
        available = self.GetAvailableGovernors(sender=sender)
        if governor not in available:
            raise dbus.exceptions.DBusException(
                f"Invalid governor: {governor}. "
                f"Available: {', '.join(available)}",
                name="io.github.serverket.cpugov.Error.InvalidGovernor"
            )

        # Check Polkit authorization
        self._check_polkit_auth(sender, POLKIT_ACTION_SET)

        # Apply to all CPUs
        cpu_dirs = self._get_cpu_dirs()
        for cpu_dir in cpu_dirs:
            path = os.path.join(cpu_dir, GOVERNOR_PATH)
            self._write_sysfs(path, governor)

        # Emit signal
        self.GovernorChanged(governor)

        # Persist the choice
        self._save_governor(governor)

        return True

    @dbus.service.method(
        INTERFACE_NAME,
        in_signature="",
        out_signature="a{sv}",
        sender_keyword="sender"
    )
    def GetCpuInfo(self, sender=None):
        """Get comprehensive CPU information."""
        cpu_dirs = self._get_cpu_dirs()
        core_count = len(cpu_dirs)

        # CPU model
        model = self._get_cpu_model()

        # Per-core info
        per_core = []
        for cpu_dir in cpu_dirs:
            core_name = os.path.basename(cpu_dir)
            core_gov = self._read_sysfs(
                os.path.join(cpu_dir, GOVERNOR_PATH)
            )
            cur_freq = self._read_sysfs(
                os.path.join(cpu_dir, CUR_FREQ_PATH)
            )
            min_freq = self._read_sysfs(
                os.path.join(cpu_dir, MIN_FREQ_PATH)
            )
            max_freq = self._read_sysfs(
                os.path.join(cpu_dir, MAX_FREQ_PATH)
            )

            per_core.append(dbus.Dictionary({
                "name": dbus.String(core_name, variant_level=1),
                "governor": dbus.String(core_gov, variant_level=1),
                "cur_freq_khz": dbus.String(cur_freq, variant_level=1),
                "min_freq_khz": dbus.String(min_freq, variant_level=1),
                "max_freq_khz": dbus.String(max_freq, variant_level=1),
            }, signature="sv"))

        # Thread count (includes HT)
        online_path = os.path.join(SYSFS_CPU_BASE, "online")
        online_str = self._read_sysfs(online_path)

        info = dbus.Dictionary({
            "model": dbus.String(model, variant_level=1),
            "core_count": dbus.Int32(core_count, variant_level=1),
            "online": dbus.String(online_str, variant_level=1),
            "per_core": dbus.Array(per_core, signature="a{sv}",
                                   variant_level=1),
        }, signature="sv")

        return info

    # ── D-Bus signals ─────────────────────────────────────────────

    @dbus.service.signal(INTERFACE_NAME, signature="s")
    def GovernorChanged(self, governor):
        """Emitted when the governor changes."""
        pass


def main():
    """Entry point for the daemon."""
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    system_bus = dbus.SystemBus()
    daemon = CPUGovDaemon(system_bus)  # noqa: F841

    loop = GLib.MainLoop()

    # Handle SIGTERM/SIGINT gracefully
    def on_signal(signum, frame):
        loop.quit()

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    print(f"cpugov-daemon: listening on {BUS_NAME}", file=sys.stderr)
    loop.run()


if __name__ == "__main__":
    main()
