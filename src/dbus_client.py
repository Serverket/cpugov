# SPDX-License-Identifier: GPL-3.0-or-later
"""D-Bus client for communicating with the cpugov-daemon."""

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gio, GLib

BUS_NAME = "io.github.serverket.cpugov"
OBJECT_PATH = "/io/github/serverket/cpugov"
INTERFACE_NAME = "io.github.serverket.cpugov"


class CPUGovDBusClient:
    """Async D-Bus client to communicate with the cpugov-daemon."""

    def __init__(self):
        self._proxy = None
        self._connection = None
        self._signal_subscription = None

    def connect(self, on_ready_cb=None, on_error_cb=None):
        """Connect to the D-Bus daemon asynchronously."""
        Gio.DBusProxy.new_for_bus(
            Gio.BusType.SYSTEM,
            Gio.DBusProxyFlags.NONE,
            None,  # interface info
            BUS_NAME,
            OBJECT_PATH,
            INTERFACE_NAME,
            None,  # cancellable
            self._on_proxy_ready,
            (on_ready_cb, on_error_cb),
        )

    def _on_proxy_ready(self, source, result, user_data):
        """Called when the D-Bus proxy is ready."""
        on_ready_cb, on_error_cb = user_data
        try:
            self._proxy = Gio.DBusProxy.new_for_bus_finish(result)

            if self._proxy.get_name_owner() is None:
                if on_error_cb:
                    on_error_cb("cpugov-daemon is not running. "
                               "Install and start the cpugov-daemon package.")
                return

            if on_ready_cb:
                on_ready_cb()
        except GLib.Error as e:
            if on_error_cb:
                on_error_cb(str(e))

    @property
    def is_connected(self):
        """Check if we have a live connection to the daemon."""
        return (self._proxy is not None
                and self._proxy.get_name_owner() is not None)

    def get_governor(self, callback):
        """Get the current governor asynchronously.

        Args:
            callback: function(governor_str, error_str_or_none)
        """
        if not self.is_connected:
            callback(None, "Not connected to daemon")
            return

        self._proxy.call(
            "GetGovernor",
            None,  # no parameters
            Gio.DBusCallFlags.NONE,
            5000,  # timeout ms
            None,  # cancellable
            self._on_get_governor_done,
            callback,
        )

    def _on_get_governor_done(self, proxy, result, callback):
        try:
            variant = proxy.call_finish(result)
            governor = variant.unpack()[0]
            callback(governor, None)
        except GLib.Error as e:
            callback(None, str(e))

    def get_available_governors(self, callback):
        """Get list of available governors.

        Args:
            callback: function(list_of_strings, error_str_or_none)
        """
        if not self.is_connected:
            callback(None, "Not connected to daemon")
            return

        self._proxy.call(
            "GetAvailableGovernors",
            None,
            Gio.DBusCallFlags.NONE,
            5000,
            None,
            self._on_get_available_done,
            callback,
        )

    def _on_get_available_done(self, proxy, result, callback):
        try:
            variant = proxy.call_finish(result)
            governors = list(variant.unpack()[0])
            callback(governors, None)
        except GLib.Error as e:
            callback(None, str(e))

    def set_governor(self, governor, callback):
        """Set the governor. Triggers Polkit auth.

        Args:
            governor: string name of the governor
            callback: function(success_bool, error_str_or_none)
        """
        if not self.is_connected:
            callback(False, "Not connected to daemon")
            return

        self._proxy.call(
            "SetGovernor",
            GLib.Variant("(s)", (governor,)),
            Gio.DBusCallFlags.NONE,
            30000,  # 30s timeout for Polkit dialog
            None,
            self._on_set_governor_done,
            callback,
        )

    def _on_set_governor_done(self, proxy, result, callback):
        try:
            variant = proxy.call_finish(result)
            success = variant.unpack()[0]
            callback(success, None)
        except GLib.Error as e:
            callback(False, str(e))

    def get_cpu_info(self, callback):
        """Get comprehensive CPU info.

        Args:
            callback: function(info_dict, error_str_or_none)
        """
        if not self.is_connected:
            callback(None, "Not connected to daemon")
            return

        self._proxy.call(
            "GetCpuInfo",
            None,
            Gio.DBusCallFlags.NONE,
            5000,
            None,
            self._on_get_cpu_info_done,
            callback,
        )

    def _on_get_cpu_info_done(self, proxy, result, callback):
        try:
            variant = proxy.call_finish(result)
            info = self._unpack_variant(variant.unpack()[0])
            callback(info, None)
        except GLib.Error as e:
            callback(None, str(e))

    def on_governor_changed(self, callback):
        """Subscribe to GovernorChanged signal.

        Args:
            callback: function(new_governor_string)
        """
        if self._proxy:
            self._proxy.connect("g-signal", self._on_signal, callback)

    def _on_signal(self, proxy, sender, signal_name, params, callback):
        if signal_name == "GovernorChanged":
            governor = params.unpack()[0]
            callback(governor)

    @staticmethod
    def _unpack_variant(value):
        """Recursively unpack GLib.Variant values to Python types."""
        if isinstance(value, GLib.Variant):
            value = value.unpack()
        if isinstance(value, dict):
            return {k: CPUGovDBusClient._unpack_variant(v)
                    for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [CPUGovDBusClient._unpack_variant(i) for i in value]
        return value
