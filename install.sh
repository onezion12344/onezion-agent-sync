#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
#  AgentDropOne — One-line installer
#
#  Usage:
#    curl -sSL https://raw.githubusercontent.com/onezion12344/AgentDropOne/main/install.sh | bash
#
#  Or with a bundle:
#    curl -sSL https://raw.githubusercontent.com/onezion12344/AgentDropOne/main/install.sh | bash -s -- bundle.zip
#
#  What it does:
#    1. Detects OS (macOS/Linux/WSL) and architecture
#    2. Installs prerequisites (Python 3.9+, Node.js, git)
#    3. Clones AgentDropOne
#    4. If bundle provided: extracts + asks about Nanobot
#    5. If no bundle: just installs the tool, ready for future use
# ═══════════════════════════════════════════════════════════
set -euo pipefail

REPO="https://github.com/onezion12344/AgentDropOne.git"
INSTALL_DIR="${AGENTDROPONE_DIR:-$HOME/.agentdropone}"
BUNDLE="${1:-}"

# ── Colors ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Banner ──────────────────────────────────────────────────
echo ""
echo -e "${PURPLE}  ╔═══════════════════════════════════════╗${NC}"
echo -e "${PURPLE}  ║     AgentDropOne Installer v0.4.0     ║${NC}"
echo -e "${PURPLE}  ║  One zip. One command. Full workspace. ║${NC}"
echo -e "${PURPLE}  ╚═══════════════════════════════════════╝${NC}"
echo ""

# ── OS Detection ────────────────────────────────────────────
detect_os() {
    OS="$(uname -s)"
    ARCH="$(uname -m)"
    DISTRO=""

    case "$OS" in
        Darwin)
            OS_NAME="macos"
            if [[ "$ARCH" == "arm64" ]]; then
                ARCH_NAME="Apple Silicon"
            else
                ARCH_NAME="Intel"
            fi
            ;;
        Linux)
            if grep -qi microsoft /proc/version 2>/dev/null; then
                OS_NAME="wsl"
            else
                OS_NAME="linux"
            fi
            ARCH_NAME="$ARCH"
            # Detect distro
            if [ -f /etc/os-release ]; then
                DISTRO=$(grep ^ID= /etc/os-release | cut -d= -f2 | tr -d '"')
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*)
            OS_NAME="windows"
            ARCH_NAME="$ARCH"
            ;;
        *)
            err "Unsupported OS: $OS"
            exit 1
            ;;
    esac

    info "Detected: ${OS_NAME} (${ARCH_NAME})"
}

# ── Prerequisites ──────────────────────────────────────────
check_cmd() { command -v "$1" &>/dev/null; }

install_brew() {
    if check_cmd brew; then
        ok "Homebrew already installed"
        return
    fi
    info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /home/linuxbrew/.linuxbrew/bin/brew shellenv 2>/dev/null)"
    ok "Homebrew installed"
}

install_python() {
    if check_cmd python3; then
        PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
            ok "Python ${PY_VER} already installed"
            return
        fi
        warn "Python ${PY_VER} found but 3.9+ required"
    fi

    info "Installing Python 3.9+..."
    case "$OS_NAME" in
        macos)
            if check_cmd brew; then
                brew install python@3.12 2>/dev/null || brew upgrade python@3.12 2>/dev/null
            else
                err "Please install Homebrew first: https://brew.sh"
                exit 1
            fi
            ;;
        linux|wsl)
            if check_cmd apt-get; then
                sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-pip python3-venv
            elif check_cmd dnf; then
                sudo dnf install -y python3 python3-pip
            elif check_cmd yum; then
                sudo yum install -y python3 python3-pip
            fi
            ;;
    esac
    ok "Python installed"
}

install_node() {
    if check_cmd node; then
        ok "Node.js $(node -v) already installed"
        return
    fi

    info "Installing Node.js..."
    case "$OS_NAME" in
        macos)
            brew install node 2>/dev/null || true
            ;;
        linux|wsl)
            if check_cmd apt-get; then
                curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - 2>/dev/null
                sudo apt-get install -y -qq nodejs 2>/dev/null
            elif check_cmd dnf; then
                sudo dnf install -y nodejs 2>/dev/null
            fi
            ;;
    esac

    if check_cmd node; then
        ok "Node.js installed"
    else
        warn "Node.js not installed — some agents may not work"
    fi
}

install_git() {
    if check_cmd git; then
        ok "Git already installed"
        return
    fi
    info "Installing Git..."
    case "$OS_NAME" in
        macos) xcode-select --install 2>/dev/null || true ;;
        linux|wsl)
            if check_cmd apt-get; then
                sudo apt-get install -y -qq git
            elif check_cmd dnf; then
                sudo dnf install -y git
            fi
            ;;
    esac
    ok "Git installed"
}

install_docker() {
    if check_cmd docker; then
        ok "Docker already installed"
        return
    fi
    info "Docker not found — skipping (optional)"
    info "Install later: https://docs.docker.com/get-docker/"
}

install_rclone() {
    if check_cmd rclone; then
        ok "rclone already installed"
        return
    fi
    info "Installing rclone..."
    case "$OS_NAME" in
        macos) brew install rclone 2>/dev/null || true ;;
        linux|wsl)
            if check_cmd apt-get; then
                sudo apt-get install -y -qq rclone 2>/dev/null || true
            fi
            ;;
    esac
    if check_cmd rclone; then
        ok "rclone installed (40+ cloud storage providers)"
    fi
}

setup_prerequisites() {
    info "Checking prerequisites..."
    echo ""

    install_git
    install_python
    install_node
    install_rclone
    install_docker

    echo ""
    ok "Prerequisites ready"
    echo ""
}

# ── Clone AgentDropOne ─────────────────────────────────────
clone_agentdropone() {
    if [ -d "$INSTALL_DIR" ]; then
        info "AgentDropOne already installed at $INSTALL_DIR"
        info "Updating..."
        cd "$INSTALL_DIR" && git pull --quiet 2>/dev/null || true
    else
        info "Cloning AgentDropOne..."
        git clone --quiet "$REPO" "$INSTALL_DIR"
    fi
    ok "AgentDropOne ready at $INSTALL_DIR"
}

# ── PATH setup ──────────────────────────────────────────────
setup_path() {
    # Add to PATH if not already there
    SHELL_RC=""
    case "$(basename "${SHELL:-zsh}")" in
        zsh)  SHELL_RC="$HOME/.zshrc" ;;
        bash) SHELL_RC="$HOME/.bashrc" ;;
    esac

    EXPORT_LINE="export PATH=\"\$HOME/.agentdropone:\$PATH\""

    if [ -n "$SHELL_RC" ] && ! grep -q "agentdropone" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# AgentDropOne" >> "$SHELL_RC"
        echo "$EXPORT_LINE" >> "$SHELL_RC"
        info "Added to PATH in $SHELL_RC"
    fi

    # Make scripts executable
    chmod +x "$INSTALL_DIR"/onesync-skills/full-migrate/*.py 2>/dev/null || true
    chmod +x "$INSTALL_DIR"/install.sh 2>/dev/null || true
}

# ── Bundle mode ─────────────────────────────────────────────
run_bundle() {
    local bundle_path="$1"

    if [ ! -f "$bundle_path" ]; then
        err "Bundle not found: $bundle_path"
        err "Provide a path to full-migration.zip"
        exit 1
    fi

    info "Running setup with bundle: $bundle_path"
    echo ""

    cd "$INSTALL_DIR"
    python3 onesync-skills/full-migrate/agentdropone-setup.py "$bundle_path"
}

# ── Docker mode ─────────────────────────────────────────────
docker_unpack() {
    local image="$1"
    info "Unpacking from Docker image: $image"

    if ! check_cmd docker; then
        err "Docker not installed"
        exit 1
    fi

    local container_id
    container_id=$(docker create "$image" 2>/dev/null)
    if [ -z "$container_id" ]; then
        err "Failed to create container from $image"
        exit 1
    fi

    docker cp "$container_id:/bundle.zip" /tmp/agentdropone-bundle.zip 2>/dev/null
    docker rm "$container_id" >/dev/null 2>&1

    if [ -f /tmp/agentdropone-bundle.zip ]; then
        ok "Bundle extracted from Docker image"
        run_bundle /tmp/agentdropone-bundle.zip
    else
        err "No bundle found in Docker image"
        exit 1
    fi
}

docker_pack() {
    info "Packing AgentDropOne as Docker image..."

    if ! check_cmd docker; then
        err "Docker not installed"
        exit 1
    fi

    # Create Dockerfile
    cat > /tmp/agentdropone-dockerfile << 'DOCKERFILE'
FROM python:3.12-slim
COPY . /app
WORKDIR /app
CMD ["python3", "onesync-skills/full-migrate/agentdropone-setup.py", "/bundle.zip"]
DOCKERFILE

    # Build image
    docker build -t agentdropone:latest -f /tmp/agentdropone-dockerfile "$INSTALL_DIR" 2>/dev/null
    ok "Docker image built: agentdropone:latest"
    info "To export: docker save agentdropone:latest | gzip > agentdropone.tar.gz"
    info "To use: docker run -v /path/to/bundle.zip:/bundle.zip agentdropone"
}

# ── Main ────────────────────────────────────────────────────
main() {
    detect_os

    # Parse special flags
    case "$BUNDLE" in
        --docker-pack)
            setup_prerequisites
            clone_agentdropone
            docker_pack
            exit 0
            ;;
        --docker-unpack=*)
            DOCKER_IMAGE="${BUNDLE#--docker-unpack=}"
            docker_unpack "$DOCKER_IMAGE"
            exit 0
            ;;
        --update)
            info "Checking for updates..."
            cd "$INSTALL_DIR" 2>/dev/null || { clone_agentdropone; }
            # Check latest tag on GitHub
            LATEST=$(curl -s https://api.github.com/repos/onezion12344/AgentDropOne/tags | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['name'])" 2>/dev/null)
            CURRENT=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")
            if [ "$LATEST" != "$CURRENT" ] && [ -n "$LATEST" ]; then
                info "Updating from $CURRENT to $LATEST..."
                git fetch --tags --quiet 2>/dev/null
                git checkout "$LATEST" --quiet 2>/dev/null
                ok "Updated to $LATEST"
            else
                ok "Already up to date ($CURRENT)"
            fi
            exit 0
            ;;
        --help|-h)
            echo "Usage:"
            echo "  install.sh                          Install AgentDropOne only"
            echo "  install.sh bundle.zip               Install + setup from bundle"
            echo "  install.sh --docker-pack            Pack as Docker image"
            echo "  install.sh --docker-unpack=image    Unpack from Docker image"
            echo "  install.sh --update                 Check & update to latest version"
            echo "  install.sh --auto                   Non-interactive: auto-export bundle"
            echo ""
            exit 0
            ;;
    esac

    setup_prerequisites
    clone_agentdropone
    setup_path

    echo ""
    echo -e "${GREEN}  ╔═══════════════════════════════════════╗${NC}"
    echo -e "${GREEN}  ║    AgentDropOne installed!             ║${NC}"
    echo -e "${GREEN}  ╚═══════════════════════════════════════╝${NC}"
    echo ""

    if [ -n "$BUNDLE" ] && [ "$BUNDLE" != "--auto" ]; then
        run_bundle "$BUNDLE"
    else
        # Ask what to do
        echo ""
        echo "  What would you like to do?"
        echo ""
        echo "    1) Restore from a bundle   (I have a bundle.zip)"
        echo "    2) Create a new bundle     (export this machine)"
        echo "    3) Just install the tool   (I'll use it later)"
        echo ""
        read -r -p "  Choose [1/2/3] " answer

        case "$answer" in
            1)
                read -r -p "  Path to bundle: " bundle_path
                if [ -f "$bundle_path" ]; then
                    run_bundle "$bundle_path"
                else
                    err "Bundle not found: $bundle_path"
                fi
                ;;
            2)
                echo ""
                info "Creating bundle from this machine..."
                echo ""
                cd "$INSTALL_DIR"
                BUNDLE_PATH="$HOME/Desktop/agentdropone-bundle.zip"
                python3 -m agentsync.cli orchestrate -o /tmp/agentdropone-export 2>/dev/null
                python3 -m agentsync.cli chat-export -o /tmp/agentdropone-export/chat-history 2>/dev/null
                cd /tmp && zip -r "$BUNDLE_PATH" agentdropone-export/ >/dev/null 2>&1
                rm -rf /tmp/agentdropone-export
                ok "Bundle created: $BUNDLE_PATH"
                ;;
            3)
                info "Tool installed. Run later with: install.sh bundle.zip"
                ;;
        esac
    fi
}

main "$@"
