# 📚 EAS Station Documentation

**Welcome!** This is your complete guide to the EAS Station emergency alert system.

> ⚠️ **IMPORTANT**: This software is experimental and for laboratory use only. Not FCC-certified for production emergency alerting.

---

## 🚀 Getting Started

**Quick Start Path:**
1. **[Installation](../README.md#quick-start)** - One command to get running
2. **[Setup Wizard](guides/SETUP_INSTRUCTIONS)** - First-run configuration
3. **[User Guide](guides/HELP)** - Daily operations

---

## 📖 Documentation by Role

### 🎯 For Operators

**Daily operations and monitoring**

| Guide | What You'll Learn |
|-------|-------------------|
| **[User Guide](guides/HELP)** | Dashboard, alerts, monitoring |
| **[Setup Instructions](guides/SETUP_INSTRUCTIONS)** | First-time configuration |
| **[HTTPS Setup](guides/HTTPS_SETUP)** | Secure access configuration |

### 🔧 For Administrators

**Deployment, security, and maintenance**

| Guide | What You'll Learn |
|-------|-------------------|
| **[Portainer Deployment](deployment/PORTAINER_DEPLOYMENT)** | Complete deployment guide |
| **[SDR Setup](hardware/SDR_SETUP)** | Radio receiver configuration |
| **[Hardware Build](hardware/reference_pi_build)** | Raspberry Pi setup |
| **[Database Troubleshooting](troubleshooting/DATABASE_CONSISTENCY_FIXES)** | PostgreSQL issues |

### 💻 For Developers

**Architecture, APIs, and contributing**

| Guide | What You'll Learn |
|-------|-------------------|
| **[Developer Guidelines](development/AGENTS)** | Code standards, architecture, testing |
| **[Frontend Documentation](frontend/FRONTEND_INDEX)** | UI components, theming |
| **[JavaScript API](frontend/JAVASCRIPT_API)** | REST API reference |
| **[Contributing](process/CONTRIBUTING)** | How to contribute |

---

## 🗺️ System Overview

### Architecture

EAS Station integrates multiple alert sources (NOAA Weather, IPAWS Federal) and processes them through a sophisticated pipeline that includes:

- 🌐 Multi-source alert aggregation
- 📻 FCC-compliant SAME encoding
- 🗺️ PostGIS spatial filtering
- 📡 SDR broadcast verification
- 🔒 Built-in HTTPS with Let's Encrypt
- ⚡ GPIO relay and LED sign control

**[View Full Architecture Details →](architecture/SYSTEM_ARCHITECTURE)**

**[View Visual Diagrams →](reference/DIAGRAMS)**

---

## 📂 Documentation Structure

```
docs/
├── guides/              ← Essential operator guides (5 files)
├── hardware/            ← SDR, GPIO, Raspberry Pi setup
├── audio/               ← Audio system documentation
├── deployment/          ← Deployment and maintenance guides
├── troubleshooting/     ← Problem-solving guides
├── development/         ← Developer documentation
├── architecture/        ← System design and theory (9 files)
├── frontend/            ← Web UI documentation
├── reference/           ← Technical reference materials
├── security/            ← Security documentation (3 files)
├── roadmap/             ← Future features and planning
├── policies/            ← Legal documents
├── process/             ← Process and reliability guides
└── resources/           ← Vendor PDFs and external docs
```

**[Complete Index](INDEX)** - Searchable list of all documentation

---

## 🎯 Common Tasks

### Setup & Configuration

- [Install EAS Station](../README.md#quick-start)
- [Configure SDR receivers](hardware/SDR_SETUP)
- [Set up HTTPS](guides/HTTPS_SETUP)
- [Connect to IPAWS](guides/ipaws_feed_integration)

### Daily Operations

- [Monitor alerts](guides/HELP#monitoring-alerts)
- [Manage boundaries](guides/HELP#managing-boundaries-and-alerts)
- [View audio streams](audio/AUDIO_MONITORING)
- [Check system health](guides/HELP#routine-operations)

### Troubleshooting

- [Database connection issues](troubleshooting/DATABASE_CONSISTENCY_FIXES)
- [SDR not detecting](hardware/SDR_SETUP#troubleshooting)
- [Audio problems](audio/AUDIO_MONITORING#troubleshooting)
- [Common errors](guides/HELP#troubleshooting)

---

## 🆘 Getting Help

1. **Check the documentation** - Start with [INDEX](INDEX)
2. **Review troubleshooting** - See [Common Issues](guides/HELP#troubleshooting)
3. **Run diagnostics** - Use built-in diagnostic tools
4. **Ask for help** - [GitHub Discussions](https://github.com/KR8MER/eas-station/discussions)
5. **Report bugs** - [GitHub Issues](https://github.com/KR8MER/eas-station/issues)

---

## 📊 Project Information

| Resource | Link |
|----------|------|
| **About** | [Project Overview](reference/ABOUT) |
| **Changelog** | [Version History](reference/CHANGELOG) |
| **Roadmap** | [Future Features](roadmap/master_todo) |
| **License** | [AGPL v3](../LICENSE) (Open Source) / [Commercial](../LICENSE-COMMERCIAL) |

### Legal & Compliance

- [Terms of Use](policies/TERMS_OF_USE)
- [Privacy Policy](policies/PRIVACY_POLICY)
- [FCC Compliance Information](reference/ABOUT#legal--compliance)

---

## 🤝 Contributing

We welcome contributions! See:

- [Contributing Guide](process/CONTRIBUTING)
- [Developer Guidelines](development/AGENTS)
- [Code Standards](development/AGENTS#code-standards)

---

**Last Updated**: 2025-12-02
**Documentation Version**: 3.1 (Reorganized documentation structure)

**[Return to Main README](../README.md)** | **[View Complete Index](INDEX)**
