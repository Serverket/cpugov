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

### Step 1: Install the Daemon (Required)

The system daemon powers the app and must be installed on your host system. We provide an automated installer script:

```bash
curl -sS https://raw.githubusercontent.com/Serverket/cpugov/main/daemon/install.sh | sudo bash
```

Alternatively, you can download the `.deb` package from the [Releases](https://github.com/Serverket/cpugov/releases) page (Debian/Ubuntu) or build manually:
```bash
meson setup builddir && meson compile -C builddir
sudo meson install -C builddir
sudo systemctl enable --now cpugov-daemon
```

### Step 2: Install the GUI

The recommended way to install the CPU Governor GUI is via Flathub:

```bash
flatpak install flathub io.github.serverket.cpugov
```

## Development

**Prerequisites:** Python 3, PyGObject, D-Bus, Polkit, systemd (Daemon), GTK4 & libadwaita (GUI).

### Building from Source

```bash
# Build and install daemon + GUI locally
meson setup builddir
meson compile -C builddir
sudo meson install -C builddir

# Run the daemon service to test
sudo systemctl start cpugov-daemon

# Build and run the Flatpak GUI sandbox
cd flatpak
flatpak-builder --user --install build-dir io.github.serverket.cpugov.yml
flatpak run io.github.serverket.cpugov
```

## License

[GPL-3.0-or-later](LICENSE)

## Acknowledgments

*"Whoever loves discipline loves knowledge, but whoever hates correction is stupid."*