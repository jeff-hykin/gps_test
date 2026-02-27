#!/usr/bin/env bash
# install_driver.sh — Install the Prolific PL2303 USB-to-serial driver (macOS)
# Used by: GlobalSat BU-353N and other PL2303-based USB GPS devices

set -euo pipefail

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[info]${NC}  $*"; }
ok()    { echo -e "${GREEN}[ ok ]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[warn]${NC}  $*"; }
die()   { echo -e "${RED}[fail]${NC}  $*" >&2; exit 1; }

# ── already installed? ───────────────────────────────────────────────────────
if ls /dev/cu.usbserial* /dev/cu.PL* 2>/dev/null | grep -q .; then
    ok "A USB serial port is already visible: $(ls /dev/cu.usbserial* /dev/cu.PL* 2>/dev/null | head -1)"
    ok "Driver appears to be working. Exiting."
    exit 0
fi

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Prolific PL2303 Driver Installer for macOS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# ── macOS version check ──────────────────────────────────────────────────────
MACOS_VERSION=$(sw_vers -productVersion)
MACOS_MAJOR=$(echo "$MACOS_VERSION" | cut -d. -f1)
info "macOS $MACOS_VERSION detected"

# ── method selection ─────────────────────────────────────────────────────────
# macOS 13+ (Ventura and later): kernel extensions are blocked by default.
# The Homebrew cask installs a kext-based driver (v2.x) which still works but
# requires approving a legacy system extension in System Settings.
# The App Store "PL2303 Serial" app uses DriverKit (no kext) and is smoother
# on Ventura/Sonoma/Sequoia — but can't be scripted past opening the App Store.

if command -v brew &>/dev/null; then
    info "Homebrew found — installing via: brew install --cask prolific-pl2303"
    echo

    brew install --cask prolific-pl2303

    echo
    ok "Package installed."
    echo
    echo -e "${YELLOW}━━━  MANUAL STEP REQUIRED  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "The driver uses a kernel extension that macOS blocks by default."
    echo
    if [[ "$MACOS_MAJOR" -ge 13 ]]; then
        echo "  1. Open: System Settings → Privacy & Security"
        echo "  2. Scroll to the bottom — you should see:"
        echo "       \"System software from 'Prolific Technology Inc.' was blocked.\""
        echo "  3. Click [Allow] and authenticate with your password."
    else
        # macOS 12 Monterey and earlier
        echo "  1. Open: System Preferences → Security & Privacy → General"
        echo "  2. Click [Allow] next to the Prolific kernel extension message."
    fi
    echo "  4. Replug the BU-353N USB cable."
    echo "  5. Confirm the device appeared:"
    echo "       ls /dev/cu.usbserial*"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
    echo "After approving and replugging, run:"
    echo "  uv run python record.py"

else
    warn "Homebrew not found."
    echo
    echo "Option A — Install Homebrew first (recommended):"
    echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    echo "  Then re-run this script."
    echo
    echo "Option B — Mac App Store (no kext, works best on Ventura+):"
    echo "  The 'PL2303 Serial' app on the App Store installs a DriverKit extension"
    echo "  that doesn't require approving a legacy kext."
    echo "  Opening App Store now …"
    echo
    open "macappstores://apps.apple.com/app/pl2303-serial/id1624835215" 2>/dev/null \
        || open "https://apps.apple.com/app/pl2303-serial/id1624835215"
    echo "  After installing from the App Store:"
    echo "    1. Launch the PL2303 Serial app once to activate the driver."
    echo "    2. Approve the driver extension in System Settings → Privacy & Security."
    echo "    3. Replug the BU-353N and check: ls /dev/cu.P*"
fi
