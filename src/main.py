#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Entry point for the CPUGov GTK application."""

import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gio  # noqa: E402

def main():
    """Application entry point."""
    resource = Gio.Resource.load(
        "@PKGDATADIR@/cpugov.gresource"
    ) if False else None  # placeholder for future gresource

    from .application import CPUGovApplication
    app = CPUGovApplication()
    return app.run(sys.argv)
