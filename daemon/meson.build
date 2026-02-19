# Daemon meson.build
# SPDX-License-Identifier: GPL-3.0-or-later

daemon_conf = configuration_data()
daemon_conf.set('PYTHON', py_installation.full_path())
daemon_conf.set('LIBEXECDIR', libexecdir)
daemon_conf.set('APP_ID', app_id)

# Install the daemon script
configure_file(
  input: 'cpugov-daemon.in',
  output: 'cpugov-daemon',
  configuration: daemon_conf,
  install: true,
  install_dir: libexecdir,
  install_mode: 'rwxr-xr-x',
)

# Install the daemon module
install_data(
  'cpugov_daemon.py',
  install_dir: libexecdir / 'cpugov',
)

# Install the systemd service
configure_file(
  input: 'io.github.serverket.cpugov.service.in',
  output: 'io.github.serverket.cpugov.service',
  configuration: daemon_conf,
  install: true,
  install_dir: datadir / 'dbus-1' / 'system-services',
)

# Install the systemd unit
configure_file(
  input: 'cpugov-daemon.systemd.service.in',
  output: 'cpugov-daemon.service',
  configuration: daemon_conf,
  install: true,
  install_dir: prefix / 'lib' / 'systemd' / 'system',
)
