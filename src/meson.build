# src meson.build
# SPDX-License-Identifier: GPL-3.0-or-later

# Configure the launcher script
configure_file(
  input: 'cpugov-gtk.in',
  output: 'cpugov-gtk',
  configuration: conf,
  install: true,
  install_dir: bindir,
  install_mode: 'rwxr-xr-x',
)

# Install Python sources
cpugov_sources = [
  '__init__.py',
  'main.py',
  'application.py',
  'window.py',
  'dbus_client.py',
]

install_data(
  cpugov_sources,
  install_dir: pkgdatadir / 'cpugov',
)
