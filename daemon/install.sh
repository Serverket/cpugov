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
  echo "Usage: curl -sS https://raw.githubusercontent.com/Serverket/cpugov/main/daemon/install.sh | sudo bash"
  exit 1
fi

echo "Installing CPU Governor Daemon..."

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

# Clone repo
echo "Cloning repository..."
git clone --depth 1 https://github.com/Serverket/cpugov.git "$TMP_DIR"

cd "$TMP_DIR"

# Build and install
echo "Building CPU Governor..."
meson setup build
meson install -C build

# Enable and start service
echo "Enabling daemon service..."
systemctl daemon-reload
systemctl enable --now cpugov-daemon

# Cleanup
echo "Cleaning up..."
cd /
rm -rf "$TMP_DIR"

echo -e "${GREEN}cpugov-daemon installed and running successfully!${NC}"
exit 0
