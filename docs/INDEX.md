# EAS Station Documentation Index

Complete documentation for **EAS Station** - an Emergency Alert System platform for amateur radio operators and emergency communications professionals.

## Quick Start

| Document | Description |
|----------|-------------|
| [Main README](https://github.com/KR8MER/eas-station/blob/main/README.md) | Installation and overview |
| [Installation Guide](installation/README) | Bare metal deployment guide |
| [Quick Start](installation/QUICKSTART) | Fast installation guide |
| [Bare Metal Quick Start](installation/QUICKSTART-BARE-METAL) | Quick start for bare metal |
| [Setup Instructions](guides/SETUP_INSTRUCTIONS) | First-run configuration |

## User Guides

| Document | Description |
|----------|-------------|
| [Help & Operations Guide](guides/HELP) | Complete operator manual |
| [HTTPS Setup](guides/HTTPS_SETUP) | SSL/TLS certificates |
| [SSL Web UI Guide](guides/SSL_WEB_UI_GUIDE) | Web-based certificate management |
| [IPAWS Integration](guides/ipaws_feed_integration) | Federal alert source setup |
| [Poller Migration Guide](guides/POLLER_MIGRATION_GUIDE) | Alert poller setup |
| [One-Button Upgrade](guides/one_button_upgrade) | Automated updates |
| [S.M.A.R.T. Setup](guides/SMART_SETUP) | NVMe and SSD health monitoring |
| [Configuration Migration](guides/CONFIGURATION_MIGRATION) | Environment variable merge utility |
| [Hardware Quickstart](guides/HARDWARE_QUICKSTART) | Hardware configuration |
| [PyCharm Debugging](guides/PYCHARM_DEBUGGING) | Remote debugging setup |

## Hardware & Audio

| Document | Description |
|----------|-------------|
| [SDR Setup Guide](hardware/SDR_SETUP) | Radio receiver configuration |
| [Audio Monitoring](audio/AUDIO_MONITORING) | Live stream viewer |
| [LED Communication](hardware/BIDIRECTIONAL_LED_COMMUNICATION) | LED sign integration |
| [Serial Adapters](hardware/SERIAL_TO_ETHERNET_ADAPTERS) | Serial device setup |
| [Waveshare RS232 WiFi](hardware/WAVESHARE_RS232_WIFI_SETUP) | Waveshare adapter setup |

## Architecture

| Document | Description |
|----------|-------------|
| [System Architecture](architecture/SYSTEM_ARCHITECTURE) | Overall system design |
| [Theory of Operation](architecture/THEORY_OF_OPERATION) | How the system works |
| [Data Flow Sequences](architecture/DATA_FLOW_SEQUENCES) | Mermaid sequence diagrams |
| [EAS Decoding Summary](architecture/EAS_DECODING_SUMMARY) | SAME decoding details |
| [EAS Monitor V3](architecture/EAS_MONITOR_V3_ARCHITECTURE) | Unified EAS monitoring (v2.29.0+) |
| [Display System](architecture/DISPLAY_SYSTEM_ARCHITECTURE) | Display subsystem design |
| [Hardware Isolation](architecture/HARDWARE_ISOLATION) | Service hardware isolation |
| [SDR Service Architecture](architecture/SDR_SERVICE_ARCHITECTURE) | SDR dual-service design |
| [SDR Service Isolation](architecture/SDR_SERVICE_ISOLATION) | SDR service separation |
| [Design Standards](architecture/DESIGN_STANDARDS) | UI/UX design system |
| [Migration](architecture/MIGRATION) | FastAPI migration status |

## Frontend

| Document | Description |
|----------|-------------|
| [User Interface Guide](frontend/USER_INTERFACE_GUIDE) | Web interface navigation |
| [JavaScript API](frontend/JAVASCRIPT_API) | REST API reference |
| [Component Library](frontend/COMPONENT_LIBRARY) | UI component reference |
| [SDR Frequency Validation](frontend/SDR_FREQUENCY_VALIDATION) | Frequency validation details |

## Troubleshooting

### SDR & Radio
| Document | Description |
|----------|-------------|
| **[SDR Quick Fix Guide](troubleshooting/SDR_QUICK_FIX_GUIDE)** | 5-minute checklist for common SDR problems |
| **[SDR Master Troubleshooting](troubleshooting/SDR_MASTER_TROUBLESHOOTING_GUIDE)** | Complete SDR diagnostic procedures |
| [SDR Troubleshooting Flowchart](troubleshooting/SDR_TROUBLESHOOTING_FLOWCHART) | Visual decision tree |
| [SDR Audio Tuning Issues](troubleshooting/SDR_AUDIO_TUNING_ISSUES) | Audio-specific SDR troubleshooting |
| [SDR Waterfall Issues](troubleshooting/SDR_WATERFALL_TROUBLESHOOTING) | Waterfall display troubleshooting |
| [SDR Streaming Issues](troubleshooting/SDR_STREAMING_ISSUES_ANALYSIS) | SDR streaming analysis |
| [Audio SDR Issues](troubleshooting/AUDIO_SDR_ISSUES_EXPLAINED) | SDR audio problems explained |

### Audio
| Document | Description |
|----------|-------------|
| [Audio Squeal Fix](troubleshooting/AUDIO_SQUEAL_FIX) | Audio feedback/squeal issues |
| [Audio Streaming Setup](troubleshooting/AUDIO_STREAMING_SETUP) | Streaming configuration |
| [Audio Dropped Packets](troubleshooting/AUDIO_DROPPED_PACKETS) | Network packet loss issues |
| [TTS Troubleshooting](troubleshooting/TTS_TROUBLESHOOTING) | Text-to-speech configuration |

### System
| Document | Description |
|----------|-------------|
| [502/504 Gateway Errors](troubleshooting/TROUBLESHOOTING_504_TIMEOUT) | Website timeout and gateway errors |
| [Environment Config Issues](troubleshooting/ENVIRONMENT_CONFIG_ISSUES) | Environment variable problems |
| [Environment File Migration](troubleshooting/ENV_FILE_MIGRATION) | Systemd env file JSON parsing |
| [Database Issues](troubleshooting/DATABASE_CONSISTENCY_FIXES) | PostgreSQL troubleshooting |
| [Database Authentication](troubleshooting/DATABASE_AUTH_FIX) | Database password and auth issues |
| [Systemd Target Cycling](troubleshooting/SYSTEMD_TARGET_CYCLING) | Fix repeated service restarts |
| [Firewall Requirements](troubleshooting/FIREWALL_REQUIREMENTS) | Network ports and firewall setup |
| [PgAdmin/Apache2 Conflict](troubleshooting/PGADMIN_APACHE2_CONFLICT) | Port conflict resolution |
| [Polling Not Working](troubleshooting/POLLING_NOT_WORKING) | Alert polling troubleshooting |
| [Update Not Pulling Changes](troubleshooting/UPDATE_NOT_PULLING_CHANGES) | Git update issues |

## Installation

| Document | Description |
|----------|-------------|
| [Installation Guide](installation/README) | Main installation guide |
| [Quick Start](installation/QUICKSTART) | Fast installation |
| [Bare Metal Quick Start](installation/QUICKSTART-BARE-METAL) | Bare metal deployment |
| [Installation Details](installation/INSTALLATION_DETAILS) | Detailed steps |
| [Alternative Methods](installation/ALTERNATIVE_METHODS) | Alternative installation methods |
| [Installation Changes](installation/Installation-Changes) | Script improvements |
| [PostgreSQL 15+ Fix](installation/PostgreSQL-15-Fix) | PostgreSQL permission fixes |

## Development

| Document | Description |
|----------|-------------|
| [Developer Guidelines](development/AGENTS) | Code standards and architecture |
| [Admin Page Refactoring](development/ADMIN_PAGE_REFACTORING) | Admin page modularization roadmap |
| [Contributing Guide](process/CONTRIBUTING) | How to contribute |

## Security

| Document | Description |
|----------|-------------|
| [Security Guide](security/SECURITY) | Security best practices |
| [Security Features](security/SECURITY_FEATURES) | Overview of security features |
| [Password Guide](security/SECURITY_PASSWORD_GUIDE) | Password management |
| [Terms of Use](policies/TERMS_OF_USE) | Usage terms |
| [Privacy Policy](policies/PRIVACY_POLICY) | Privacy information |

## Reference

| Document | Description |
|----------|-------------|
| [About EAS Station](reference/ABOUT) | Project background |
| [DASDEC-III Comparison](reference/DASDEC_COMPARISON) | Feature gap analysis vs. commercial DASDEC-III |
| [Changelog](reference/CHANGELOG) | Version history |
| [Diagrams Index](reference/DIAGRAMS) | Visual documentation index |
| [FIPS Codes Update](reference/FIPS_CODES_UPDATE) | FIPS/SAME code data sources |
| [Ohio EAS Documentation](reference/OHIO_EAS_DOCUMENTATION) | Ohio EAS plan reference |
| [Certification Reliability Plan](process/certification_reliability_plan) | FCC certification readiness |
| [Feature Roadmap](roadmap/dasdec3-feature-roadmap) | Planned features |
| [Future Enhancements](roadmap/FUTURE_ENHANCEMENTS) | Future feature ideas |
| [Disk Space Cleanup](maintenance/DISK_SPACE_CLEANUP) | Storage maintenance |

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

**Last Updated**: 2026-02-13
**For questions or contributions, see the [Contributing Guide](process/CONTRIBUTING)**
