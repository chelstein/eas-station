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
| [HTTPS Setup](guides/HTTPS_SETUP.md) | SSL/TLS certificates |
| [SSL Web UI Guide](guides/SSL_WEB_UI_GUIDE.md) | Web-based certificate management |
| [IPAWS Integration](guides/ipaws_feed_integration.md) | Federal alert source setup |
| [Poller Migration Guide](guides/POLLER_MIGRATION_GUIDE.md) | Alert poller setup |
| [One-Button Upgrade](guides/one_button_upgrade.md) | Automated updates |
| [Tailscale VPN Setup](guides/TAILSCALE_SETUP.md) | Secure remote access via Tailscale mesh VPN |
| [S.M.A.R.T. Setup](guides/SMART_SETUP.md) | NVMe and SSD health monitoring |
| [Configuration Migration](guides/CONFIGURATION_MIGRATION.md) | Environment variable merge utility |
| [Hardware Quickstart](guides/HARDWARE_QUICKSTART.md) | Hardware configuration |
| [PyCharm Debugging](guides/PYCHARM_DEBUGGING.md) | Remote debugging setup |

## Hardware & Audio

| Document | Description |
|----------|-------------|
| [SDR Setup Guide](hardware/SDR_SETUP.md) | Radio receiver configuration |
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
| [Migration](architecture/MIGRATION.md) | FastAPI migration status |

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
| [Audio Squeal Fix](troubleshooting/AUDIO_SQUEAL_FIX.md) | Audio feedback/squeal issues |
| [Audio Streaming Setup](troubleshooting/AUDIO_STREAMING_SETUP.md) | Streaming configuration |
| [Audio Dropped Packets](troubleshooting/AUDIO_DROPPED_PACKETS.md) | Network packet loss issues |
| [TTS Troubleshooting](troubleshooting/TTS_TROUBLESHOOTING.md) | Text-to-speech configuration |

### System
| Document | Description |
|----------|-------------|
| [502/504 Gateway Errors](troubleshooting/TROUBLESHOOTING_504_TIMEOUT.md) | Website timeout and gateway errors |
| [Environment Config Issues](troubleshooting/ENVIRONMENT_CONFIG_ISSUES.md) | Environment variable problems |
| [Environment File Migration](troubleshooting/ENV_FILE_MIGRATION.md) | Systemd env file JSON parsing |
| [Database Issues](troubleshooting/DATABASE_CONSISTENCY_FIXES.md) | PostgreSQL troubleshooting |
| [Database Authentication](troubleshooting/DATABASE_AUTH_FIX.md) | Database password and auth issues |
| [Systemd Target Cycling](troubleshooting/SYSTEMD_TARGET_CYCLING.md) | Fix repeated service restarts |
| [Firewall Requirements](troubleshooting/FIREWALL_REQUIREMENTS.md) | Network ports and firewall setup |
| [PgAdmin/Apache2 Conflict](troubleshooting/PGADMIN_APACHE2_CONFLICT.md) | Port conflict resolution |
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
| [Installation Changes](installation/Installation-Changes.md) | Script improvements |
| [PostgreSQL 15+ Fix](installation/PostgreSQL-15-Fix.md) | PostgreSQL permission fixes |

## Development

| Document | Description |
|----------|-------------|
| [Developer Guidelines](development/AGENTS.md) | Code standards and architecture |
| [Admin Page Refactoring](development/ADMIN_PAGE_REFACTORING.md) | Admin page modularization roadmap |
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
| [FIPS Codes Update](reference/FIPS_CODES_UPDATE.md) | FIPS/SAME code data sources |
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
├── troubleshooting/ # Problem-solving guides
└── archive/         # Historical documentation
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

**Last Updated**: 2026-02-17
**For questions or contributions, see the [Contributing Guide](process/CONTRIBUTING.md)**
