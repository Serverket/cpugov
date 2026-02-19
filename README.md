<div align="center">
  <img src="data/io.github.serverket.cpugov.svg" width="128" alt="CPU Governor">
  <h1>CPU Governor</h1>
</div>

A modern GTK4/libadwaita application for controlling your Linux CPU frequency scaling governor.

![License](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)
![Platform](https://img.shields.io/badge/platform-Linux-green)

<p align="center">
  <img src="screenshots/main-window.png" width="100%">
</p>

## Features

- **Toggle CPU governors** — Switch between performance, powersave, and other available governors with a single click
- **Persistent across reboots** — Your chosen governor is saved and automatically restored on boot
- **Real-time monitoring** — Live per-core frequency display updated every 2 seconds
- **Secure privilege management** — Uses Polkit for authorization, no running the GUI as root
- **Modern GNOME design** — Built with GTK4 and libadwaita, supports dark/light themes
- **Multilanguage** — English, Spanish, Portuguese, Japanese, Chinese, and Italian
- **Flatpak-ready** — Sandboxed GUI with host-side daemon architecture

## Architecture

CPU Governor uses a two-component architecture:

| Component | Description |
|-----------|-------------|
| **cpugov-daemon** | A D-Bus system service (runs as root) that reads/writes CPU governors via sysfs |
| **cpugov-gtk** | A GTK4/libadwaita GUI (runs as user, optionally in Flatpak sandbox) that communicates with the daemon via D-Bus |

```
[GTK4 GUI] ──D-Bus──▶ [cpugov-daemon] ──sysfs──▶ [/sys/.../scaling_governor]
                            │                          ▲
                       [Polkit Auth]             [Boot restore]
                                                       │
                                          [/var/lib/cpugov/config.json]
```

### Persistence

When you select a governor, the daemon saves your choice to `/var/lib/cpugov/config.json`. On the next boot, `cpugov-daemon.service` reads the config and restores the governor automatically — no manual action needed.

## Installation

### Step 1: Install the system daemon

The daemon must be installed on the host system (outside the Flatpak sandbox):

```bash
# Build and install from source
meson setup builddir
meson compile -C builddir
sudo meson install -C builddir

# Enable the daemon to start on boot
sudo systemctl daemon-reload
sudo systemctl enable --now cpugov-daemon

# Or install the .deb package (Debian/Ubuntu)
sudo dpkg -i cpugov-daemon_0.1.0-1_all.deb
```

### Step 2: Install the GUI

**From Flathub (recommended):**
```bash
flatpak install flathub io.github.serverket.cpugov
```

**From source:**
```bash
meson setup builddir
meson compile -C builddir
sudo meson install -C builddir
cpugov-gtk
```

## Development

### Dependencies

**Daemon:**
- Python 3
- python3-dbus
- python3-gi (PyGObject)
- polkit
- systemd

**GUI:**
- Python 3
- GTK4
- libadwaita
- python3-gi (PyGObject)

### Building

```bash
# Full build (daemon + GUI)
meson setup builddir
meson compile -C builddir
sudo meson install -C builddir

# Test the daemon
sudo systemctl start cpugov-daemon
gdbus call --system --dest io.github.serverket.cpugov \
  --object-path /io/github/serverket/cpugov \
  --method io.github.serverket.cpugov.GetGovernor

# Build Flatpak (GUI only)
cd flatpak
flatpak-builder --user --install build-dir io.github.serverket.cpugov.yml
flatpak run io.github.serverket.cpugov
```

### Building the Debian package

```bash
dpkg-buildpackage -us -uc -b
sudo dpkg -i ../cpugov-daemon_0.1.0-1_all.deb
```

## License

[GPL-3.0-or-later](LICENSE)

## Acknowledgments

*"Whoever loves discipline loves knowledge, but whoever hates correction is stupid."*