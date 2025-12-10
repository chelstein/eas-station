# EAS Station Bare Metal Makefile
# Convenience commands for managing the installation

.PHONY: help install status logs start stop restart enable disable update uninstall build-iso

help:
	@echo "EAS Station Bare Metal Management"
	@echo "=================================="
	@echo ""
	@echo "Installation:"
	@echo "  make install        Install EAS Station on current system"
	@echo "  make build-iso      Build bootable ISO image"
	@echo ""
	@echo "Service Management:"
	@echo "  make start          Start all services"
	@echo "  make stop           Stop all services"
	@echo "  make restart        Restart all services"
	@echo "  make enable         Enable auto-start on boot"
	@echo "  make disable        Disable auto-start on boot"
	@echo ""
	@echo "Monitoring:"
	@echo "  make status         Show service status"
	@echo "  make logs           Interactive log viewer"
	@echo ""
	@echo "Maintenance:"
	@echo "  make update         Update to latest version"
	@echo "  make uninstall      Remove EAS Station"
	@echo ""
	@echo "All commands require root privileges (use sudo make ...)"

install:
	@echo "Installing EAS Station..."
	@bash scripts/install.sh

build-iso:
	@echo "Building bootable ISO image..."
	@bash scripts/build-iso.sh

status:
	@bash scripts/status.sh

logs:
	@bash scripts/logs.sh

start:
	@echo "Starting EAS Station services..."
	@systemctl start eas-station.target
	@echo "Services started. Check status with: sudo make status"

stop:
	@echo "Stopping EAS Station services..."
	@systemctl stop eas-station.target
	@echo "Services stopped."

restart:
	@echo "Restarting EAS Station services..."
	@systemctl restart eas-station.target
	@echo "Services restarted. Check status with: sudo make status"

enable:
	@echo "Enabling auto-start on boot..."
	@systemctl enable eas-station.target
	@echo "Auto-start enabled."

disable:
	@echo "Disabling auto-start on boot..."
	@systemctl disable eas-station.target
	@echo "Auto-start disabled."

update:
	@echo "Updating EAS Station..."
	@bash scripts/update.sh

uninstall:
	@echo "Uninstalling EAS Station..."
	@bash scripts/uninstall.sh
