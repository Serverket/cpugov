# SPDX-License-Identifier: GPL-3.0-or-later
"""Main application window for CPUGov."""

import gettext
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk, Pango

from . import APP_ID
from .dbus_client import CPUGovDBusClient

_ = gettext.gettext


def _fmt_freq(khz_str):
    """Format a frequency in kHz to a human-readable string."""
    try:
        khz = int(khz_str)
        if khz >= 1_000_000:
            return f"{khz / 1_000_000:.2f} GHz"
        elif khz >= 1_000:
            return f"{khz / 1_000:.0f} MHz"
        return f"{khz} kHz"
    except (ValueError, TypeError):
        return "—"


class CPUGovWindow(Adw.ApplicationWindow):
    """The main CPUGov window."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._dbus = CPUGovDBusClient()
        self._refresh_timer = None
        self._available_governors = []
        self._current_governor = None
        self._governor_buttons = {}
        self._core_rows = {}
        self._settings = None

        # Try to load settings
        try:
            self._settings = Gio.Settings.new(APP_ID)
        except Exception:
            pass

        self._setup_window()
        self._build_ui()
        self._connect_daemon()

    def _setup_window(self):
        """Configure the window properties."""
        self.set_title(_("CPU Governor"))
        self.set_icon_name(APP_ID)
        self.set_default_size(
            self._settings.get_int("window-width") if self._settings else 480,
            self._settings.get_int("window-height") if self._settings else 640,
        )

        # Save window size on close
        self.connect("close-request", self._on_close_request)
        
        # Focus management: grab focus when mapped
        self.connect("map", self._on_map)

    def _on_map(self, widget):
        """Called when the window is mapped; ensure focus is correct."""
        GLib.timeout_add(100, self._ensure_focus)

    def _on_close_request(self, window):
        """Save window dimensions before closing."""
        if self._settings:
            width, height = self.get_default_size()
            self._settings.set_int("window-width", width)
            self._settings.set_int("window-height", height)

        if self._refresh_timer:
            GLib.source_remove(self._refresh_timer)
            self._refresh_timer = None

        return False

    # ── UI Construction ───────────────────────────────────────────

    def _build_ui(self):
        """Build the entire UI hierarchy."""
        # Header bar with icon + title
        header = Adw.HeaderBar()

        # Custom title widget: icon + label side by side
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        title_box.set_halign(Gtk.Align.CENTER)

        icon = Gtk.Image.new_from_icon_name(APP_ID)
        icon.set_pixel_size(20)
        title_box.append(icon)

        title_label = Gtk.Label(label=_("CPU Governor"))
        title_label.add_css_class("title")
        title_box.append(title_label)

        header.set_title_widget(title_box)

        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_model = Gio.Menu()
        menu_model.append(_("About CPU Governor"), "app.about")
        menu_model.append(_("Quit"), "app.quit")
        menu_button.set_menu_model(menu_model)
        header.pack_end(menu_button)

        # Main content
        self._main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Toolbar view (Adw pattern)
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header)
        toolbar_view.set_content(self._main_box)
        self.set_content(toolbar_view)

        # Build the initial "connecting" state
        self._build_connecting_view()

    def _build_connecting_view(self):
        """Show a spinner while connecting to the daemon."""
        self._clear_main()

        status = Adw.StatusPage(
            title=_("Connecting…"),
            description=_("Reaching the CPU Governor daemon"),
            icon_name="system-run-symbolic",
        )
        spinner = Gtk.Spinner()
        spinner.start()
        spinner.set_size_request(48, 48)
        spinner.set_halign(Gtk.Align.CENTER)
        status.set_child(spinner)

        self._main_box.append(status)

    def _build_error_view(self, message):
        """Show an error message with retry option and install instructions."""
        self._clear_main()

        status = Adw.StatusPage(
            title=_("Connection Error"),
            description=message,
            icon_name="dialog-error-symbolic",
        )

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        vbox.set_halign(Gtk.Align.CENTER)
        vbox.set_margin_top(12)

        # Installation command group
        install_group = Adw.PreferencesGroup(
            title=_("To install the required host daemon, run:")
        )
        
        cmd_row = Adw.ActionRow(
            subtitle="curl -sS https://raw.githubusercontent.com/Serverket/cpugov/master/daemon/install.sh | sudo bash"
        )
        cmd_row.add_css_class("property")
        
        # Copy button
        copy_btn = Gtk.Button(icon_name="edit-copy-symbolic", valign=Gtk.Align.CENTER)
        copy_btn.set_tooltip_text(_("Copy to clipboard"))
        copy_btn.add_css_class("flat")
        copy_btn.connect("clicked", lambda btn: self.get_clipboard().set("curl -sS https://raw.githubusercontent.com/Serverket/cpugov/master/daemon/install.sh | sudo bash"))
        cmd_row.add_suffix(copy_btn)

        install_group.add(cmd_row)
        vbox.append(install_group)

        # Retry button
        retry_btn = Gtk.Button(label=_("Retry Connection"))
        retry_btn.set_halign(Gtk.Align.CENTER)
        retry_btn.add_css_class("suggested-action")
        retry_btn.add_css_class("pill")
        retry_btn.connect("clicked", self._on_retry)
        vbox.append(retry_btn)

        status.set_child(vbox)

        self._main_box.append(status)

    def _build_main_view(self):
        """Build the main governor control view."""
        self._clear_main()

        scrolled = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vexpand=True,
        )

        clamp = Adw.Clamp(maximum_size=600, margin_top=24, margin_bottom=24,
                          margin_start=12, margin_end=12)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(content)
        scrolled.set_child(clamp)
        self._main_box.append(scrolled)

        # ── Governor Switcher ─────────────────────────────────────
        gov_group = Adw.PreferencesGroup(title=_("Governor"))

        self._governor_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=0,
            halign=Gtk.Align.CENTER,
            margin_top=8,
            margin_bottom=8,
        )
        self._governor_box.add_css_class("linked")

        # We'll populate buttons after getting available governors
        gov_group.add(self._governor_box)
        content.append(gov_group)

        # ── CPU Info ──────────────────────────────────────────────
        self._info_group = Adw.PreferencesGroup(title=_("Processor"))
        self._model_row = Adw.ActionRow(title=_("Model"))
        self._cores_row = Adw.ActionRow(title=_("Cores"))
        self._freq_range_row = Adw.ActionRow(title=_("Frequency Range"))

        self._info_group.add(self._model_row)
        self._info_group.add(self._cores_row)
        self._info_group.add(self._freq_range_row)
        content.append(self._info_group)

        # ── Per-Core Status ───────────────────────────────────────
        self._cores_group = Adw.PreferencesGroup(title=_("Per-Core Status"))
        content.append(self._cores_group)

        # Start refresh
        self._request_refresh()
        interval = 2
        if self._settings:
            interval = self._settings.get_int("refresh-interval")
        self._refresh_timer = GLib.timeout_add_seconds(
            interval, self._on_refresh_tick
        )

    # ── D-Bus Connection ──────────────────────────────────────────

    def _connect_daemon(self):
        """Initiate connection to the D-Bus daemon."""
        self._dbus.connect(
            on_ready_cb=self._on_daemon_ready,
            on_error_cb=self._on_daemon_error,
        )

    def _on_daemon_ready(self):
        """Called when the D-Bus proxy is ready."""
        self._build_main_view()

        # Subscribe to governor change signals
        self._dbus.on_governor_changed(self._on_governor_signal)

        # Get available governors
        self._dbus.get_available_governors(self._on_available_governors)

    def _on_daemon_error(self, message):
        """Called when daemon connection fails."""
        self._build_error_view(message)

    def _on_retry(self, button):
        """Retry daemon connection."""
        self._build_connecting_view()
        self._connect_daemon()

    # ── Data Callbacks ────────────────────────────────────────────

    def _on_available_governors(self, governors, error):
        """Called when available governors are received."""
        if error:
            return

        self._available_governors = governors
        self._rebuild_governor_buttons()
        self._request_refresh()
        
        # Explicitly grab focus after a short delay once everything is built
        GLib.timeout_add(100, self._ensure_focus)

    def _ensure_focus(self):
        """Force the window and the current governor button to have focus."""
        self.present()
        if self._current_governor in self._governor_buttons:
            btn = self._governor_buttons[self._current_governor]
            btn.grab_focus()
            self.set_default_widget(btn)
        return False

    def _rebuild_governor_buttons(self):
        """Create buttons for each available governor.

        Both buttons are always visible. The active governor gets a
        highlighted (accent) style; inactive ones stay neutral.
        """
        # Clear existing
        child = self._governor_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._governor_box.remove(child)
            child = next_child
        self._governor_buttons.clear()
        
        # We don't reset self._current_governor here anymore to keep selection visible

        # Icon mapping for known governors using standard GTK symbolic icons
        icons = {
            "performance": "power-profile-performance-symbolic",      # Lightning/Performance
            "powersave": "battery-level-100-symbolic",    # Battery/Powersave
            "ondemand": "media-playlist-shuffle-symbolic",# Shuffle/Ondemand
            "conservative": "go-down-symbolic",           # Down/Conservative
            "schedutil": "applications-system-symbolic",  # System/Schedutil
            "userspace": "avatar-default-symbolic",       # User/Userspace
        }

        first_btn = None
        for gov in self._available_governors:
            icon_name = icons.get(gov, "preferences-system-symbolic")
            
            # Create a box to hold the icon and label
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            box.set_halign(Gtk.Align.CENTER)
            
            icon = Gtk.Image.new_from_icon_name(icon_name)
            label = Gtk.Label(label=gov.capitalize())
            
            box.append(icon)
            box.append(label)

            btn = Gtk.ToggleButton()
            btn.set_child(box)
            btn.set_focus_on_click(True)
            
            if first_btn:
                btn.set_group(first_btn)
            else:
                first_btn = btn
                
            btn.connect("toggled", self._on_governor_toggled, gov)
            
            # Highlight immediately if this is the active governor
            if gov == self._current_governor:
                btn.handler_block_by_func(self._on_governor_toggled)
                btn.set_active(True)
                btn.add_css_class("suggested-action")
                btn.handler_unblock_by_func(self._on_governor_toggled)
                self.set_default_widget(btn)

            self._governor_box.append(btn)
            self._governor_buttons[gov] = btn

    def _on_governor_toggled(self, button, governor):
        """Handle governor button toggle."""
        # Only care about the button becoming active
        if not button.get_active():
            return
            
        # Don't re-apply if it's already the current governor
        if governor == self._current_governor:
            return
        # Request the change via D-Bus
        self._dbus.set_governor(governor, self._on_set_governor_result)

    def _on_set_governor_result(self, success, error):
        """Called after attempting to set the governor."""
        if error:
            dialog = Adw.AlertDialog(
                heading=_("Failed to Set Governor"),
                body=str(error),
            )
            dialog.add_response("ok", _("OK"))
            dialog.set_default_response("ok")
            dialog.present(self)

            # Refresh to restore correct button state
            self._request_refresh()

    def _on_governor_signal(self, governor):
        """Handle GovernorChanged signal from the daemon."""
        self._update_governor_ui(governor)

    def _update_governor_ui(self, governor):
        """Update button states to match the actual governor."""
        if governor == self._current_governor:
            return
            
        self._current_governor = governor

        if governor in self._governor_buttons:
            for gov, btn in self._governor_buttons.items():
                if gov == governor:
                    btn.handler_block_by_func(self._on_governor_toggled)
                    btn.set_active(True)
                    btn.add_css_class("suggested-action")
                    btn.handler_unblock_by_func(self._on_governor_toggled)
                    
                    # Ensure the window has a valid focus widget
                    self.set_default_widget(btn)
                    if not self.get_focus():
                        btn.grab_focus()
                else:
                    btn.handler_block_by_func(self._on_governor_toggled)
                    btn.remove_css_class("suggested-action")
                    btn.set_active(False)
                    btn.handler_unblock_by_func(self._on_governor_toggled)

    # ── Refresh / Polling ─────────────────────────────────────────

    def _on_refresh_tick(self):
        """Called periodically by the refresh timer."""
        if not self._dbus.is_connected:
            return False  # Stop the timer

        self._request_refresh()
        return True  # Continue

    def _request_refresh(self):
        """Request updated data from the daemon."""
        self._dbus.get_governor(self._on_governor_refresh)
        self._dbus.get_cpu_info(self._on_cpu_info_refresh)

    def _on_governor_refresh(self, governor, error):
        """Update governor display."""
        if error or governor is None:
            return
        self._update_governor_ui(governor)

    def _on_cpu_info_refresh(self, info, error):
        """Update CPU info display."""
        if error or info is None:
            return

        # Update processor info rows
        model = info.get("model", "Unknown")
        core_count = info.get("core_count", 0)
        online = info.get("online", "?")

        self._model_row.set_subtitle(model)
        self._cores_row.set_subtitle(
            _("%(count)d cores (online: %(online)s)") % {
                "count": core_count, "online": online
            }
        )

        # Per-core info
        per_core = info.get("per_core", [])
        if per_core:
            # Update frequency range from first core
            first = per_core[0] if per_core else {}
            min_freq = first.get("min_freq_khz", "0")
            max_freq = first.get("max_freq_khz", "0")
            self._freq_range_row.set_subtitle(
                f"{_fmt_freq(min_freq)} – {_fmt_freq(max_freq)}"
            )

        # Update per-core rows
        self._update_core_rows(per_core)

    def _update_core_rows(self, per_core):
        """Update or create per-core display rows."""
        existing_names = set(self._core_rows.keys())
        current_names = set()

        for core_info in per_core:
            name = core_info.get("name", "?")
            current_names.add(name)
            gov = core_info.get("governor", "?")
            cur_freq = core_info.get("cur_freq_khz", "0")

            if name in self._core_rows:
                # Update existing row
                row = self._core_rows[name]
                row.set_subtitle(
                    f"{gov}  •  {_fmt_freq(cur_freq)}"
                )
            else:
                # Create new row
                core_num = name.replace("cpu", "")
                row = Adw.ActionRow(
                    title=_("Core %s") % core_num,
                    subtitle=f"{gov}  •  {_fmt_freq(cur_freq)}",
                )
                row.add_css_class("property")
                self._cores_group.add(row)
                self._core_rows[name] = row

        # Remove stale rows
        for name in existing_names - current_names:
            row = self._core_rows.pop(name)
            self._cores_group.remove(row)

    # ── Utility ───────────────────────────────────────────────────

    def _clear_main(self):
        """Remove all children from the main box."""
        child = self._main_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._main_box.remove(child)
            child = next_child
