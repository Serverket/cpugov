# SPDX-License-Identifier: GPL-3.0-or-later
"""CPUGov Adw.Application subclass."""

import gettext
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk

from . import APP_ID, VERSION
from .window import CPUGovWindow

_ = gettext.gettext


class CPUGovApplication(Adw.Application):
    """The main CPUGov application."""

    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

        self.set_resource_base_path("/io/github/serverket/cpugov")

    def do_activate(self):
        """Called when the application is activated."""
        win = self.props.active_window
        if not win:
            win = CPUGovWindow(application=self)
        win.present()

    def do_startup(self):
        """Called when the application starts."""
        Adw.Application.do_startup(self)
        self._setup_actions()

    def _setup_actions(self):
        """Set up application actions."""
        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self._on_quit)
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<primary>q"])

    def _on_about(self, action, param):
        """Show the about dialog."""
        about = Adw.AboutDialog(
            application_name=_("CPU Governor"),
            application_icon=APP_ID,
            version=VERSION,
            developer_name=_("Manuel \"Serverket\" Hernandez"),
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/Serverket/cpugov",
            issue_url="https://github.com/Serverket/cpugov/issues",
            developers=[_("Manuel \"Serverket\" Hernandez"), _("CPUGov Contributors")],
            copyright=_("© 2026 Manuel \"Serverket\" Hernandez and Contributors"),
            comments=_("Control your CPU frequency scaling governor"),
        )
        about.present(self.props.active_window)

    def _on_quit(self, action, param):
        """Quit the application."""
        self.quit()
