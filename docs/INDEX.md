# EAS Station Documentation Index

Complete documentation for **EAS Station** - an Emergency Alert System platform for amateur radio operators and emergency communications professionals.

## Quick Start

| Document | Description |
|----------|-------------|
| [Main README](https://github.com/KR8MER/eas-station/blob/main/README.md) | Installation and overview |
| [Installation Guide](installation/README.md) | Bare metal deployment guide |
| [Quick Start](installation/QUICKSTART.md) | Fast installation guide |
| [Bare Metal Quick Start](installation/QUICKSTART-BARE-METAL.md) | Quick start for bare metal |
| [Setup Instructions](guides/SETUP_INSTRUCTIONS.md) | First-run configuration |

## User Guides

| Document | Description |
|----------|-------------|
| [Help & Operations Guide](guides/HELP.md) | Complete operator manual |
| [Manual EAS Events & Broadcast Builder](guides/MANUAL_EAS_EVENTS.md) | Create and send manual EAS broadcasts and RWT tests |
| [eas-config Tool](guides/EAS_CONFIG_TOOL.md) | Interactive terminal configuration utility |
| [Multi-Factor Authentication (TOTP)](guides/MFA_TOTP_SETUP.md) | Set up and manage 2FA for admin accounts |
| [API Key Management](guides/API_KEY_MANAGEMENT.md) | Create, rotate, and manage REST API keys |
| [Database Backups](guides/DATABASE_BACKUPS.md) | Backup strategy, restore procedures, and scheduling |
| [Analytics and Reporting](guides/ANALYTICS_AND_REPORTING.md) | Alert trends, anomaly detection, and compliance reports |
| [Audit Log Review](guides/AUDIT_LOG_REVIEW.md) | Review security events and user action logs |
| [Icecast Streaming Setup](guides/ICECAST_STREAMING_SETUP.md) | Configure Icecast audio streaming server |
| [HTTPS Setup](guides/HTTPS_SETUP.md) | SSL/TLS certificates |
| [SSL Web UI Guide](guides/SSL_WEB_UI_GUIDE.md) | Web-based certificate management |
| [IPAWS Integration](guides/ipaws_feed_integration.md) | Federal alert source setup |
| [One-Button Upgrade](guides/one_button_upgrade.md) | Automated updates |
| [Tailscale VPN Setup](guides/TAILSCALE_SETUP.md) | Secure remote access via Tailscale mesh VPN |
| [S.M.A.R.T. Setup](guides/SMART_SETUP.md) | NVMe and SSD health monitoring |
| [Hardware Quickstart](guides/HARDWARE_QUICKSTART.md) | Hardware configuration |

## Hardware & Audio

| Document | Description |
|----------|-------------|
| [SDR Setup Guide](hardware/SDR_SETUP.md) | Radio receiver configuration |
| [GPIO Relay Wiring](hardware/GPIO_RELAY_WIRING.md) | Transmitter relay wiring, pin assignments, and safety |
| [VFD Display Setup](hardware/VFD_DISPLAY_SETUP.md) | Noritake GU140x32F vacuum fluorescent display |
| [NeoPixel LED Control](hardware/NEOPIXEL_LED_CONTROL.md) | WS2812B addressable LED strip integration |
| [GPS HAT Setup](hardware/GPS_HAT_SETUP.md) | Adafruit Ultimate GPS HAT for precision time and location |
| [Audio Monitoring](audio/AUDIO_MONITORING.md) | Live stream viewer |
| [LED Communication](hardware/BIDIRECTIONAL_LED_COMMUNICATION.md) | LED sign integration |
| [Serial Adapters](hardware/SERIAL_TO_ETHERNET_ADAPTERS.md) | Serial device setup |
| [Waveshare RS232 WiFi](hardware/WAVESHARE_RS232_WIFI_SETUP.md) | Waveshare adapter setup |

## Architecture

| Document | Description |
|----------|-------------|
| [System Architecture](architecture/SYSTEM_ARCHITECTURE.md) | Overall system design |
| [Theory of Operation](architecture/THEORY_OF_OPERATION.md) | How the system works |
| [Data Flow Sequences](architecture/DATA_FLOW_SEQUENCES.md) | Mermaid sequence diagrams |
| [EAS Decoding Summary](architecture/EAS_DECODING_SUMMARY.md) | SAME decoding details |
| [EAS Monitor V3](architecture/EAS_MONITOR_V3_ARCHITECTURE.md) | Unified EAS monitoring (v2.29.0+) |
| [Display System](architecture/DISPLAY_SYSTEM_ARCHITECTURE.md) | Display subsystem design |
| [Hardware Isolation](architecture/HARDWARE_ISOLATION.md) | Service hardware isolation |
| [SDR Service Architecture](architecture/SDR_SERVICE_ARCHITECTURE.md) | SDR dual-service design |
| [SDR Service Isolation](architecture/SDR_SERVICE_ISOLATION.md) | SDR service separation |
| [Design Standards](architecture/DESIGN_STANDARDS.md) | UI/UX design system |

## Frontend

| Document | Description |
|----------|-------------|
| [User Interface Guide](frontend/USER_INTERFACE_GUIDE.md) | Web interface navigation |
| [JavaScript API](frontend/JAVASCRIPT_API.md) | REST API reference |
| [Component Library](frontend/COMPONENT_LIBRARY.md) | UI component reference |
| [SDR Frequency Validation](frontend/SDR_FREQUENCY_VALIDATION.md) | Frequency validation details |

## Troubleshooting

### SDR & Radio
| Document | Description |
|----------|-------------|
| **[SDR Quick Fix Guide](troubleshooting/SDR_QUICK_FIX_GUIDE.md)** | 5-minute checklist for common SDR problems |
| **[SDR Master Troubleshooting](troubleshooting/SDR_MASTER_TROUBLESHOOTING_GUIDE.md)** | Complete SDR diagnostic procedures |
| [SDR Troubleshooting Flowchart](troubleshooting/SDR_TROUBLESHOOTING_FLOWCHART.md) | Visual decision tree |
| [SDR Audio Tuning Issues](troubleshooting/SDR_AUDIO_TUNING_ISSUES.md) | Audio-specific SDR troubleshooting |
| [SDR Waterfall Issues](troubleshooting/SDR_WATERFALL_TROUBLESHOOTING.md) | Waterfall display troubleshooting |
| [SDR Streaming Issues](troubleshooting/SDR_STREAMING_ISSUES_ANALYSIS.md) | SDR streaming analysis |
| [Audio SDR Issues](troubleshooting/AUDIO_SDR_ISSUES_EXPLAINED.md) | SDR audio problems explained |

### Audio
| Document | Description |
|----------|-------------|
| [Audio Streaming Setup](troubleshooting/AUDIO_STREAMING_SETUP.md) | Streaming configuration |
| [Audio Dropped Packets](troubleshooting/AUDIO_DROPPED_PACKETS.md) | Network packet loss issues |
| [TTS Troubleshooting](troubleshooting/TTS_TROUBLESHOOTING.md) | Text-to-speech configuration |

### System
| Document | Description |
|----------|-------------|
| [502/504 Gateway Errors](troubleshooting/TROUBLESHOOTING_504_TIMEOUT.md) | Website timeout and gateway errors |
| [Systemd Target Cycling](troubleshooting/SYSTEMD_TARGET_CYCLING.md) | Fix repeated service restarts |
| [Firewall Requirements](troubleshooting/FIREWALL_REQUIREMENTS.md) | Network ports and firewall setup |
| [Polling Not Working](troubleshooting/POLLING_NOT_WORKING.md) | Alert polling troubleshooting |
| [Update Not Pulling Changes](troubleshooting/UPDATE_NOT_PULLING_CHANGES.md) | Git update issues |

## Installation

| Document | Description |
|----------|-------------|
| [Installation Guide](installation/README.md) | Main installation guide |
| [Quick Start](installation/QUICKSTART.md) | Fast installation |
| [Bare Metal Quick Start](installation/QUICKSTART-BARE-METAL.md) | Bare metal deployment |
| [Installation Details](installation/INSTALLATION_DETAILS.md) | Detailed steps |
| [Alternative Methods](installation/ALTERNATIVE_METHODS.md) | Alternative installation methods |

## Development

| Document | Description |
|----------|-------------|
| [Developer Guidelines](development/AGENTS.md) | Code standards and architecture |
| [Contributing Guide](process/CONTRIBUTING.md) | How to contribute |

## Security

| Document | Description |
|----------|-------------|
| [Security Guide](security/SECURITY.md) | Security best practices |
| [Security Features](security/SECURITY_FEATURES.md) | Overview of security features |
| [Password Guide](security/SECURITY_PASSWORD_GUIDE.md) | Password management |
| [Terms of Use](policies/TERMS_OF_USE.md) | Usage terms |
| [Privacy Policy](policies/PRIVACY_POLICY.md) | Privacy information |

## Reference

| Document | Description |
|----------|-------------|
| [About EAS Station](reference/ABOUT.md) | Project background |
| [DASDEC-III Comparison](reference/DASDEC_COMPARISON.md) | Feature gap analysis vs. commercial DASDEC-III |
| [Changelog](reference/CHANGELOG.md) | Version history |
| [Diagrams Index](reference/DIAGRAMS.md) | Visual documentation index |
| [Ohio EAS Documentation](reference/OHIO_EAS_DOCUMENTATION.md) | Ohio EAS plan reference |
| [Certification Reliability Plan](process/certification_reliability_plan.md) | FCC certification readiness |
| [Feature Roadmap](roadmap/dasdec3-feature-roadmap.md) | Planned features |
| [Future Enhancements](roadmap/FUTURE_ENHANCEMENTS.md) | Future feature ideas |
| [Disk Space Cleanup](maintenance/DISK_SPACE_CLEANUP.md) | Storage maintenance |

## File Organization

```
docs/
├── architecture/    # System architecture and design
├── audio/           # Audio monitoring
├── development/     # Developer documentation
├── frontend/        # Web UI documentation
├── guides/          # User and operator guides
├── hardware/        # SDR and hardware setup
├── installation/    # Installation guides
├── maintenance/     # System maintenance
├── policies/        # Legal documents
├── process/         # Contributing and certification
├── reference/       # Reference materials
├── roadmap/         # Feature planning
├── security/        # Security documentation
└── troubleshooting/ # Problem-solving guides
```

## Finding Information

- **New Users**: Start with [Setup Instructions](guides/SETUP_INSTRUCTIONS)
- **Operators**: See [Help & Operations Guide](guides/HELP)
- **Developers**: Review [Developer Guidelines](development/AGENTS)

## Getting Help

1. **Check Documentation**: Start with the relevant guide above
2. **Search Issues**: [GitHub Issues](https://github.com/KR8MER/eas-station/issues)
3. **Community Support**: [GitHub Discussions](https://github.com/KR8MER/eas-station/discussions)

---

**Last Updated**: 2026-03-20
**For questions or contributions, see the [Contributing Guide](process/CONTRIBUTING.md)**
