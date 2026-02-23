#!/usr/bin/env bash
# CPU Governor Daemon Installer
# https://github.com/Serverket/cpugov

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Error: This script must be run as root (using sudo).${NC}"
  echo "Usage: curl -sS https://raw.githubusercontent.com/Serverket/cpugov/master/daemon/install.sh | sudo bash"
  exit 1
fi

# Prevent duplication: check if a Debian package is actually INSTALLED
# We use dpkg-query to distinguish between "installed" and "removed but configured"
if dpkg-query -W -f='${db:Status-Status}' cpugov 2>/dev/null | grep -q "^installed$"; then
  echo -e "${RED}Error: CPU Governor is already installed via a Debian package (.deb).${NC}"
  echo "Please uninstall it first using: sudo apt remove cpugov"
  echo "This prevents conflicting versions between /usr and /usr/local."
  exit 1
fi

echo "Installing CPU Governor Daemon..."

# Self-Cleanup: Ensure no stale files from previous manual installs exist in /usr/local
# We EXPLICITLY preserve /var/lib/cpugov/config.json
echo "Cleaning up previous manual installation (preserving config)..."
rm -f /usr/local/bin/cpugov
rm -f /usr/local/bin/cpugov-gtk
rm -f /usr/local/bin/cpugov-daemon
rm -rf /usr/local/share/cpugov
rm -f /usr/local/share/applications/io.github.serverket.cpugov.desktop
rm -f /usr/local/share/metainfo/io.github.serverket.cpugov.metainfo.xml
rm -f /usr/local/share/dbus-1/system.d/io.github.serverket.cpugov.conf
rm -f /usr/local/share/polkit-1/actions/io.github.serverket.cpugov.policy
rm -f /usr/local/lib/systemd/system/cpugov-daemon.service
# Note: /var/lib/cpugov is NOT touched.

# Check dependencies
MISSING_DEPS=""
for dep in git meson ninja; do
  if ! command -v $dep &> /dev/null; then
    MISSING_DEPS="$MISSING_DEPS $dep"
  fi
done

if [ -n "$MISSING_DEPS" ]; then
  echo -e "${RED}Error: Missing dependencies:${NC}$MISSING_DEPS"
  echo "Please install them using your package manager."
  echo "Ubuntu/Debian: apt install git meson ninja-build"
  echo "Fedora: dnf install git meson ninja-build"
  echo "Arch Linux: pacman -S git meson ninja"
  exit 1
fi

TMP_DIR="/tmp/cpugov-install"

# Clean up any previous install dir
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"

# Pre-installation cleanup of legacy files (prevents duplicated menu entries)
echo "Removing legacy files..."
rm -f /usr/local/share/applications/io.github.cpugov.CPUGov.desktop
rm -f /usr/share/applications/io.github.cpugov.CPUGov.desktop
rm -f /etc/dbus-1/system.d/io.github.cpugov.CPUGov.conf

# Determine source (local or remote)
REPO_ROOT="$(dirname "$(dirname "$(readlink -f "$0")")")"
if [ -d "$REPO_ROOT/.git" ] && [ -f "$REPO_ROOT/meson.build" ]; then
  echo "Detected local repository at $REPO_ROOT. Using local files for installation..."
  cp -a "$REPO_ROOT"/. "$TMP_DIR/"
  # Remove build artifacts and other local-only files to ensure a clean build
  rm -rf "$TMP_DIR/builddir" "$TMP_DIR/obj-x86_64-linux-gnu" "$TMP_DIR/subprojects"
else
  echo "Cloning repository from GitHub..."
  git clone --depth 1 https://github.com/Serverket/cpugov.git "$TMP_DIR"
fi

# Ensure configuration directory exists with correct permissions
echo "Ensuring configuration directory exists..."
mkdir -p /var/lib/cpugov
chmod 755 /var/lib/cpugov

cd "$TMP_DIR"

# Build and install
echo "Building CPU Governor..."
if ! meson setup build -Ddaemon=true; then
  echo -e "${RED}Error: Meson setup failed!${NC}"
  exit 1
fi

if ! meson install -C build; then
  echo -e "${RED}Error: Meson install failed!${NC}"
  exit 1
fi

# Ensure Polkit finds the policy if installed to /usr/local
if [ -f /usr/local/share/polkit-1/actions/io.github.serverket.cpugov.policy ]; then
  echo "Symlinking Polkit policy..."
  ln -sf /usr/local/share/polkit-1/actions/io.github.serverket.cpugov.policy /usr/share/polkit-1/actions/
fi

# Ensure D-Bus finds the system bus policy if installed to /usr/local
if [ -f /usr/local/share/dbus-1/system.d/io.github.serverket.cpugov.conf ]; then
  echo "Symlinking D-Bus system policy..."
  ln -sf /usr/local/share/dbus-1/system.d/io.github.serverket.cpugov.conf /usr/share/dbus-1/system.d/
  
  # Reload D-Bus config BEFORE starting the service
  if command -v dbus-send > /dev/null 2>&1; then
      echo "Reloading D-Bus configuration..."
      dbus-send --system --type=method_call --dest=org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.ReloadConfig || true
  fi
fi

# Enable and start service
echo "Enabling daemon service..."
systemctl daemon-reload
if ! systemctl enable --now cpugov-daemon; then
  echo -e "${RED}Error: Failed to enable or start cpugov-daemon.service!${NC}"
  echo "Check 'journalctl -xeu cpugov-daemon.service' for details."
  exit 1
fi

# Final service restart to be safe (if already running)
systemctl restart cpugov-daemon || true

# Verify it's actually running
echo "Verifying service status..."
if ! systemctl is-active --quiet cpugov-daemon; then
  echo -e "${RED}Error: Service started, but is not active.${NC}"
  exit 1
fi

# Cleanup
echo "Cleaning up..."
update-desktop-database /usr/local/share/applications &>/dev/null || true
cd /
rm -rf "$TMP_DIR"

echo -e "${GREEN}cpugov-daemon installed and running successfully!${NC}"
exit 0
