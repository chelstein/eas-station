# 📚 EAS Station Documentation Index

Welcome to the complete documentation for **EAS Station** - an Emergency Alert System platform built for amateur radio operators and emergency communications professionals.

## 🚀 Quick Start

If you're new to EAS Station, start here:

| Document | Description |
|----------|-------------|
| [Main README](https://github.com/KR8MER/eas-station/blob/main/README.md) | Installation and overview |
| [Setup Instructions](guides/SETUP_INSTRUCTIONS) | First-run configuration |
| [Portainer Deployment](deployment/PORTAINER_DEPLOYMENT) | Container-based setup |

## 📊 Visual Documentation

| Diagram | Description |
|---------|-------------|
| [All Diagrams Index](reference/DIAGRAMS) | Complete visual documentation |

## 👥 User Documentation

### Essential Guides
| Document | Description |
|----------|-------------|
| [Help & Operations Guide](guides/HELP) | Complete operator manual |
| [Setup Instructions](guides/SETUP_INSTRUCTIONS) | Initial configuration |
| [PyCharm Remote Debugging](guides/PYCHARM_DEBUGGING) | Debug on Raspberry Pi with PyCharm/VS Code |
| [HTTPS Setup](guides/HTTPS_SETUP) | SSL/TLS certificates |
| [IPAWS Integration](guides/ipaws_feed_integration) | Federal alert source setup |
| [One-Button Upgrade](guides/one_button_upgrade) | Automated updates |
| [Poller Config Migration](guides/POLLER_CONFIG_MIGRATION) | Poller configuration migration |

### Hardware & Audio
| Document | Description |
|----------|-------------|
| [SDR Setup Guide](hardware/SDR_SETUP) | Radio receiver configuration |
| [Audio Monitoring](audio/AUDIO_MONITORING) | Live stream viewer |

## 🛠️ Developer Documentation

| Document | Description |
|----------|-------------|
| [Developer Guidelines](development/AGENTS) | Code standards and architecture |
| [Contributing Guide](process/CONTRIBUTING) | How to contribute |
| [System Architecture](architecture/SYSTEM_ARCHITECTURE) | Overall system design |
| [Theory of Operation](architecture/THEORY_OF_OPERATION) | How the system works |
| [Data Flow Sequences](architecture/DATA_FLOW_SEQUENCES) | Detailed mermaid diagrams |
| [Display System Architecture](architecture/DISPLAY_SYSTEM_ARCHITECTURE) | Display subsystem diagrams |
| [EAS Decoding Summary](architecture/EAS_DECODING_SUMMARY) | Architecture analysis |
| [Hardware Isolation](architecture/HARDWARE_ISOLATION) | Container hardware isolation |
| [SDR Service Isolation](architecture/SDR_SERVICE_ISOLATION) | SDR service architecture |
| [SDR Service Architecture](architecture/SDR_SERVICE_ARCHITECTURE) | SDR dual-service design |
| [SDR Architecture Refactoring](architecture/SDR_ARCHITECTURE_REFACTORING) | Future refactoring plan |
| [Architecture Issues](architecture/ARCHITECTURE_ISSUES) | Known architecture issues |

## 🎨 Frontend Documentation

| Document | Description |
|----------|-------------|
| [User Interface Guide](frontend/USER_INTERFACE_GUIDE) | Web interface navigation |
| [JavaScript API](frontend/JAVASCRIPT_API) | API documentation |
| [Component Library](frontend/COMPONENT_LIBRARY) | UI component reference |

## 🔧 Troubleshooting

| Document | Description |
|----------|-------------|
| [Database Issues](troubleshooting/DATABASE_CONSISTENCY_FIXES) | PostgreSQL troubleshooting |
| [SDR Waterfall Issues](troubleshooting/SDR_WATERFALL_TROUBLESHOOTING) | SDR troubleshooting |
| [Firewall Requirements](troubleshooting/FIREWALL_REQUIREMENTS) | Network ports and firewall setup |
| [IPv6 Connectivity](troubleshooting/FIX_IPV6_CONNECTIVITY) | IPv6 troubleshooting |
| [Airspy Container Fix](troubleshooting/AIRSPY_CONTAINER_FIX) | Airspy SDR container issues |
| [Audio Squeal Fix](troubleshooting/AUDIO_SQUEAL_FIX) | Audio feedback/squeal issues |
| [Audio SDR Issues](troubleshooting/AUDIO_SDR_ISSUES_EXPLAINED) | SDR audio problems explained |
| [Containerization Fixes](troubleshooting/CONTAINERIZATION_FIXES) | Docker container issues |
| [SDR Streaming Issues](troubleshooting/SDR_STREAMING_ISSUES_ANALYSIS) | SDR streaming analysis |

## 🔐 Security & Legal

| Document | Description |
|----------|-------------|
| [Security Guide](security/SECURITY) | Security best practices |
| [Password Guide](security/SECURITY_PASSWORD_GUIDE) | Password management |
| [Container Permissions](security/CONTAINER_PERMISSIONS) | Container security audit |
| [Security & Bug Fixes](security/SECURITY_AND_BUG_FIXES) | Security fixes and patches |
| [Terms of Use](policies/TERMS_OF_USE) | Usage terms |
| [Privacy Policy](policies/PRIVACY_POLICY) | Privacy information |

## 🛡️ Reliability & Compliance

| Document | Description |
|----------|-------------|
| [Certification-Grade Reliability Plan](process/certification_reliability_plan) | Timing, failover, and audit controls for certification readiness |

## 📈 Project Information

| Document | Description |
|----------|-------------|
| [About EAS Station](reference/ABOUT) | Project background |
| [Changelog](reference/CHANGELOG) | Version history |
| [Ohio EAS Documentation](reference/OHIO_EAS_DOCUMENTATION) | Ohio EAS system reference |
| [Diagrams Index](reference/DIAGRAMS) | Visual documentation index |
| [Release Notes v1.0.0](reference/RELEASE_NOTES_v1.0.0) | Version 1.0.0 release notes |
| [Feature Roadmap](roadmap/dasdec3-feature-roadmap) | Planned features |

## 📁 File Organization

```
docs/
├── guides/          # 6 essential user guides
├── architecture/    # 10 system architecture docs
├── audio/           # 1 audio monitoring guide
├── deployment/      # 1 deployment guide
├── development/     # 1 developer guide
├── frontend/        # 3 UI documentation files
├── hardware/        # 1 SDR setup guide
├── troubleshooting/ # 9 problem-solving guides
├── security/        # 4 security guides
├── reference/       # 5 reference materials
├── roadmap/         # 1 roadmap document
├── policies/        # 2 legal documents
└── process/         # 2 process and reliability guides
```

## 🔍 Finding Information

### By User Type
- **New Users**: Start with [Setup Instructions](guides/SETUP_INSTRUCTIONS)
- **Operators**: See [Help & Operations Guide](guides/HELP)
- **Admins**: Check [Portainer Deployment](deployment/PORTAINER_DEPLOYMENT)
- **Developers**: Review [Developer Guidelines](development/AGENTS)

## 🆘 Getting Help

1. **Check Documentation**: Start with the relevant guide above
2. **Search Issues**: [GitHub Issues](https://github.com/KR8MER/eas-station/issues)
3. **Community Support**: [GitHub Discussions](https://github.com/KR8MER/eas-station/discussions)

## 📊 Documentation Statistics

| Metric | Value |
|--------|-------|
| Total Documentation Files | 46 |
| Essential User Guides | 6 |
| Architecture Documents | 10 |
| Troubleshooting Guides | 9 |
| Security Documents | 4 |
| Reference Materials | 5 |
| Total Directories | 13 |

---

**Last Updated**: 2025-12-02
**Version**: 4.3 (Moved root-level docs, fixed broken links)
**For questions or contributions, see the [Contributing Guide](process/CONTRIBUTING)**
