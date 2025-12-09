# <img src="static/img/eas-system-wordmark.svg" alt="EAS Station" width="48" height="48" style="vertical-align: middle;"> EAS Station

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue?style=flat-square&logo=gnu&logoColor=white)](https://www.gnu.org/licenses/agpl-3.0)
[![Commercial License](https://img.shields.io/badge/License-Commercial-green?style=flat-square)](LICENSE-COMMERCIAL)

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-CA2C39?style=flat-square&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL + PostGIS](https://img.shields.io/badge/PostgreSQL%20%2B%20PostGIS-17%20%2F%203.4-0093D0?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7%20Alpine-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io/)

[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-v2-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Gunicorn](https://img.shields.io/badge/Gunicorn-23.0-499848?style=flat-square&logo=gunicorn&logoColor=white)](https://gunicorn.org/)
[![Nginx](https://img.shields.io/badge/Nginx-Alpine-009639?style=flat-square&logo=nginx&logoColor=white)](https://nginx.org/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=flat-square&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9.4-199900?style=flat-square&logo=leaflet&logoColor=white)](https://leafletjs.com/)

> **A professional Emergency Alert System (EAS) platform for monitoring, broadcasting, and verifying NOAA and IPAWS alerts**

EAS Station is a software-defined drop-in replacement for commercial EAS encoder/decoder hardware, built on commodity hardware like Raspberry Pi. It provides comprehensive alert processing with FCC-compliant SAME encoding, multi-source aggregation, PostGIS spatial intelligence, SDR verification, and integrated LED signage.

---

!!! warning "**IMPORTANT: Laboratory Use Only**"
    EAS Station is experimental software for research and development. It is **not FCC-certified** and must only be used in controlled test environments. Never use for production emergency alerting.

---

## 📋 State EAS Plan Documentation

**Ohio Emergency Alert System Plan** (FCC-approved March 2019) is now documented:
- **[📖 Ohio EAS Documentation](docs/reference/OHIO_EAS_DOCUMENTATION.md)** - Complete plan, station listings, test procedures
- **[⚠️ Critical Issues Status](docs/architecture/CRITICAL_ISSUES_STATUS.md)** - System status and known issues

**Event Code Update (Nov 2025)**: Added 6 critical missing codes to codebase:
- **SQW** (Snow Squall Warning) - Sudden whiteout conditions on highways
- **ISW** (Ice Storm Warning) - Significant ice accumulation
- **WCW** (Wind Chill Warning) - Dangerous wind chills
- **LSW** (Lake Effect Snow Warning) - Heavy lake effect snow
- **LFW** (Lakeshore Flood Warning) - Lake Erie lakeshore flooding
- **EQE** (Earthquake Early Warning) - ShakeAlert system warning

The system now supports **67 event codes** (up from 61) and can encode/decode all missing codes using the originator reference in plain language output.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🌐 **Multi-Source Ingestion** | NOAA Weather, IPAWS federal alerts, and custom CAP feeds |
| 📻 **FCC-Compliant SAME** | Specific Area Message Encoding per FCC Part 11 |
| 🗺️ **Geographic Intelligence** | PostGIS spatial filtering with county/state/polygon support |
| 📡 **SDR Verification** | Automated broadcast verification with RTL-SDR/Airspy |
| 🔒 **Built-in HTTPS** | Automatic SSL/TLS with Let's Encrypt, nginx reverse proxy |
| 🎨 **Modern Web UI** | Responsive Bootstrap 5 interface with real-time updates |
| ⚡ **Hardware Integration** | GPIO relay control, LED signs, multiple audio outputs |

## 🏗️ Architecture

**Separated Service Design** - Modern, reliable, production-grade architecture:

```mermaid
graph LR
    A[Alert Sources<br/>NOAA/IPAWS] --> P[Poller Service]
    P --> DB[(PostgreSQL<br/>PostGIS)]
    DB --> W[Web Service<br/>Flask]
    DB --> AS[Audio Service<br/>SAME Encoder]
    AS --> TX[Transmitter]
    W --> UI[Web Browser]

    style A fill:#3b82f6,color:#fff
    style DB fill:#8b5cf6,color:#fff
    style W fill:#10b981,color:#fff
    style AS fill:#f59e0b,color:#000
    style UI fill:#6366f1,color:#fff
```

**Benefits:**
- ✅ **Reliable** - Services isolated (web crashes don't affect audio)
- ✅ **Simple** - No complex worker coordination
- ✅ **Fast** - Dedicated resources per service
- ✅ **Debuggable** - Separate logs, independent restart

## 🚀 Quick Start

### Deployment Flow

```mermaid
flowchart TD
    START[Clone Repository] --> ENV[Copy .env.example to .env]
    ENV --> CONFIG{Configure<br/>Settings?}
    CONFIG -->|Later| BUILD[docker compose up -d]
    CONFIG -->|Now| EDIT[Edit .env file]
    EDIT --> BUILD
    BUILD --> HTTPS{Production<br/>or Local?}
    HTTPS -->|Production| DOMAIN[Set DOMAIN_NAME in .env]
    HTTPS -->|Local| ACCEPT[Accept self-signed cert]
    DOMAIN --> RESTART[docker compose restart]
    ACCEPT --> WEB[Open https://localhost]
    RESTART --> WEB
    WEB --> DONE[✓ Running!]

    style START fill:#3b82f6,color:#fff
    style BUILD fill:#8b5cf6,color:#fff
    style DONE fill:#10b981,color:#fff
```

### One-Command Installation

```bash
git clone https://github.com/KR8MER/eas-station.git && \
cd eas-station && \
cp .env.example .env && \
sudo docker compose up -d --build
```

Then open **https://localhost** in your browser (HTTPS enabled by default).

> 💡 **Next Steps**:
> - For production with Let's Encrypt: Set `DOMAIN_NAME` in `.env` and restart
> - For localhost: Accept the self-signed certificate warning (safe for testing)
> - Edit `.env` with your configuration, then restart: `sudo docker compose restart`

### Prerequisites

- Docker Engine 24+ with Compose V2
- PostgreSQL 14+ with PostGIS (can use embedded container)
- 4GB RAM (8GB recommended)
- Internet connection for alert polling

> **Note**: Most Docker commands require root privileges. If you're running as a non-root user, prefix commands with `sudo`. Alternatively, add your user to the `docker` group (see [Docker Post-Installation Steps](https://docs.docker.com/engine/install/linux-postinstall/)).

## 📚 Documentation

```mermaid
graph TD
    START{What do you<br/>want to do?}
    START -->|Install & Setup| SETUP[📖 Quick Start Guide]
    START -->|Configure Hardware| HW[📡 SDR Setup<br/>🎧 Audio Setup]
    START -->|Daily Operations| OPS[📘 User Guide<br/>🛠️ Admin Guide]
    START -->|Development| DEV[💻 Developer Guide<br/>🎨 Frontend Docs]

    SETUP --> DOCS[📚 Full Documentation]
    HW --> DOCS
    OPS --> DOCS
    DEV --> DOCS

    style START fill:#3b82f6,color:#fff
    style DOCS fill:#10b981,color:#fff
```

### Quick Links

| For... | Start Here |
|--------|------------|
| **First Time Setup** | [Setup Instructions](docs/guides/SETUP_INSTRUCTIONS) → [Quick Start](#quick-start) |
| **Radio Configuration** | [SDR Setup Guide](docs/hardware/SDR_SETUP) |
| **Daily Operations** | [User Guide](docs/guides/HELP) |
| **Deployment** | [Portainer Guide](docs/deployment/PORTAINER_DEPLOYMENT.md) |
| **Development** | [Developer Guide](docs/development/AGENTS) |
| **Debugging on Pi** | [PyCharm Remote Debugging Guide](docs/guides/PYCHARM_DEBUGGING) |

**📖 [Complete Documentation Index](docs/INDEX)** - Searchable topics and detailed guides

## 📡 API Endpoints

EAS Station exposes a comprehensive REST API for automation and integrations:

- [Endpoint reference](docs/frontend/JAVASCRIPT_API.md) – Complete request/response catalog and authentication model
- [Architecture overview](docs/architecture/SYSTEM_ARCHITECTURE.md) – How the API interacts with pollers, database, and broadcast services
- [JavaScript API Guide](docs/frontend/JAVASCRIPT_API.md) – Using the JavaScript client to control GPIO and audio devices

> Tip: All API routes are namespaced under `/api/`. Use the `X-API-Key` header generated from the Configuration → API Keys page.

## 🏗️ Architecture

```mermaid
graph TB
    A[Alert Sources<br/>NOAA, IPAWS] -->|CAP XML| B[Alert Poller]
    B -->|Store| C[(PostgreSQL<br/>+ PostGIS)]
    C -->|Query| D[Web Application<br/>Flask]
    C -->|Trigger| E[Broadcast Service<br/>SAME Encoder]
    E -->|Audio| F[Transmitter]
    E -->|Verify| G[SDR Receiver]
    D -->|Control| E
    D -->|Monitor| G
    D -->|Display| H[Web Browser]

    style A fill:#3b82f6,color:#fff
    style C fill:#8b5cf6,color:#fff
    style D fill:#10b981,color:#fff
    style E fill:#f59e0b,color:#000
    style H fill:#6366f1,color:#fff
```

### Core Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web Application** | Flask 3.0 + Bootstrap 5 | User interface and API |
| **Alert Poller** | Python async | CAP feed monitoring |
| **Database** | PostgreSQL 17 + PostGIS 3.4 | Spatial data storage |
| **Broadcast Engine** | Python + ALSA | SAME encoding and audio |
| **SDR Service** | RTL-SDR/Airspy | Transmission verification |

## 🎯 Use Cases

<table>
<tr>
<td width="50%">

**Broadcasters**
- Replace $5,000-$7,000 commercial encoders
- Multi-station coordination
- Automated compliance logging

**Amateur Radio**
- Emergency communications testing
- Alert relay networks
- Training and education

</td>
<td width="50%">

**Alert Distribution**
- Custom alert distribution
- Geographic targeting
- Integration with existing systems

**Developers**
- CAP protocol experimentation
- Alert system research
- Custom integrations

</td>
</tr>
</table>

## ⚙️ System Requirements

### Recommended Hardware

| Component | Specification |
|-----------|---------------|
| **Compute** | Raspberry Pi 5 (8GB) or equivalent x86 |
| **Control** | Multi-relay GPIO HAT |
| **Audio** | USB sound card or Pi HAT |
| **SDR** | RTL-SDR v3 or Airspy |
| **Storage** | External SSD (50GB+) |

### Software Requirements

**For Docker deployment (recommended)**:
- Docker Engine 24+ with Compose V2
- PostgreSQL 14+ with PostGIS 3+ (provided in docker-compose.yml)

**For source installation**:
- Python 3.11+
- PostgreSQL 14+ with PostGIS 3+
- System packages (see below)

### System Package Dependencies

**Required for audio streaming**:
- `ffmpeg` - Audio codec library for MP3/AAC/OGG stream decoding
- `libpq-dev` - PostgreSQL client library headers

**Optional (for specific features)**:
- `icecast2` - Audio streaming server (recommended for production)
- `python3-soapysdr` + `soapysdr-module-rtlsdr` - SDR receiver support
- `espeak` / `libespeak-ng1` - Text-to-speech synthesis
- `libusb-1.0-0` - USB SDR hardware support

> 📘 **Docker users**: All system packages are pre-installed in the container.
>
> 📘 **Source installation**: See [Setup Instructions](docs/guides/SETUP_INSTRUCTIONS.md) for complete installation guide.

## 🛠️ Configuration

Edit `.env` with your settings:

```bash
# Core settings
SECRET_KEY=generate-with-python-secrets-module
POSTGRES_HOST=alerts-db
POSTGRES_PASSWORD=your-secure-password

# Your location
DEFAULT_COUNTY_NAME=Your County
DEFAULT_STATE_CODE=XX
DEFAULT_ZONE_CODES=XXZ001,XXC001

# Enable broadcast (optional)
EAS_BROADCAST_ENABLED=false
EAS_ORIGINATOR=WXR
EAS_STATION_ID=YOURCALL

# Resource allocation (adjust for your RAM)
# For 16GB RAM systems, quadruple these values
TMPFS_SDR_SERVICE=64M
TMPFS_AUDIO_SERVICE=128M
TMPFS_APP=128M
```

See [Configuration Guide](docs/guides/HELP) for complete reference.  
See [tmpfs Configuration](docs/deployment/TMPFS_CONFIGURATION.md) for RAM optimization.

## 📊 System Diagrams

Professional flowcharts and block diagrams illustrating system architecture and workflows:

<table>
<tr>
<td width="50%">
<a href="docs/assets/diagrams/alert-processing-pipeline.svg">
<img src="docs/assets/diagrams/alert-processing-pipeline.svg" alt="Alert Processing Pipeline" />
</a>
<p align="center"><em><strong>Alert Processing Pipeline</strong></em><br/>CAP ingestion, validation, and storage workflow</p>
</td>
<td width="50%">
<a href="docs/assets/diagrams/broadcast-workflow.svg">
<img src="docs/assets/diagrams/broadcast-workflow.svg" alt="Broadcast Workflow" />
</a>
<p align="center"><em><strong>EAS Broadcast Workflow</strong></em><br/>SAME generation and transmission process</p>
</td>
</tr>
<tr>
<td width="50%">
<a href="docs/assets/diagrams/sdr-setup-flow.svg">
<img src="docs/assets/diagrams/sdr-setup-flow.svg" alt="SDR Setup Flow" />
</a>
<p align="center"><em><strong>SDR Setup & Configuration</strong></em><br/>Complete radio receiver setup guide</p>
</td>
<td width="50%">
<a href="docs/assets/diagrams/audio-source-routing.svg">
<img src="docs/assets/diagrams/audio-source-routing.svg" alt="Audio Source Routing" />
</a>
<p align="center"><em><strong>Audio Source Architecture</strong></em><br/>Multi-source audio routing and monitoring</p>
</td>
</tr>
<tr>
<td colspan="2">
<a href="docs/assets/diagrams/system-deployment-hardware.svg">
<img src="docs/assets/diagrams/system-deployment-hardware.svg" alt="Hardware Deployment" />
</a>
<p align="center"><em><strong>Hardware Deployment Architecture</strong></em><br/>Raspberry Pi 5 reference configuration with peripherals</p>
</td>
</tr>
</table>

📖 **[View all architectural diagrams →](docs/architecture/SYSTEM_ARCHITECTURE)**

## 📊 Screenshots

<table>
<tr>
<td width="50%">
<img src="static/img/eas-system-wordmark.svg" alt="Dashboard" />
<p align="center"><em>Main Dashboard</em></p>
</td>
<td width="50%">
<img src="static/img/raspberry-pi-hero.svg" alt="Admin Panel" />
<p align="center"><em>Administration Panel</em></p>
</td>
</tr>
</table>

## 🤝 Contributing

We welcome contributions! Please see:

- [Contributing Guide](docs/process/CONTRIBUTING)
- [Code Standards](docs/development/AGENTS)
- [Development Setup](docs/development/AGENTS)

### Development

```bash
# Clone repository
git clone https://github.com/KR8MER/eas-station.git
cd eas-station

# Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure database
cp .env.example .env
# Edit .env with local database settings

# Run development server
python app.py
```

## 🆘 Support

- 📖 **Documentation**: [Complete Docs](docs/INDEX)
- 🔧 **Diagnostic Tools**: [Troubleshooting Scripts](scripts/diagnostics/)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/KR8MER/eas-station/discussions)
- 🐛 **Issues**: [GitHub Issues](https://github.com/KR8MER/eas-station/issues)
- 📡 **Community**: Join our amateur radio forums

> **Quick Diagnostics**: 
> - **SDR not working?** Run `bash scripts/collect_sdr_diagnostics.sh` or see [SDR Quick Fix Guide](docs/troubleshooting/SDR_QUICK_FIX_GUIDE.md)
> - **Connection issues?** Run `bash scripts/diagnostics/troubleshoot_connection.sh` 
> - **See all tools**: [scripts/diagnostics/README.md](scripts/diagnostics/README.md)

> **Alert Self-Test**: Open **Tools → Alert Verification** and use the built-in Alert Self-Test panel to replay bundled RWT captures and confirm your configured FIPS codes still trigger activations.

## ⚖️ Legal & Compliance

!!! danger "FCC Compliance Warning"
    **EAS Station generates valid EAS SAME headers and attention tones.** Unauthorized broadcast violates FCC regulations and can result in substantial fines:

    - 2015 iHeartMedia: [$1M settlement](https://docs.fcc.gov/public/attachments/DA-15-199A1.pdf)
    - 2014 Multiple Networks: [$1.9M settlement](https://docs.fcc.gov/public/attachments/DA-14-1097A1.pdf)

    Always work in shielded test environments. Never connect to production broadcast chains.

See [Terms of Use](docs/policies/TERMS_OF_USE) and [FCC Compliance](docs/reference/ABOUT) for details.

## 📈 Roadmap

Current development focuses on:

- ✅ **Core Features**: Multi-source ingestion, SAME encoding, geographic filtering
- ✅ **System Diagnostics**: Web-based validation and health checking tool
- ✅ **Stream Profiles**: Multi-bitrate Icecast streaming configuration
- 🔄 **Hardware Parity**: Advanced relay control, multi-receiver coordination
- ⏳ **Certification**: FCC Part 11 compliance documentation
- ⏳ **Advanced Features**: Cloud sync, mobile app, multi-site coordination

See [Feature Roadmap](docs/roadmap/dasdec3-feature-roadmap.md) for complete details.

### Recent Additions (November 2025)

- **System Diagnostics Tool** (`/diagnostics`) - Web-based installation validation with Docker, database, and configuration checks
- **Stream Profile Manager** (`/settings/stream-profiles`) - Configure multiple Icecast streams with different bitrates and formats
- **Quick Start Guide** - 15-minute deployment guide with common scenarios and troubleshooting

See [Changelog](docs/reference/CHANGELOG.md) for detailed documentation of recent changes.

## 📜 License

EAS Station is available under **dual licensing**:

### Open Source License (AGPL v3)

For open-source projects and non-commercial use, EAS Station is licensed under the [GNU Affero General Public License v3 (AGPL-3.0)](LICENSE).

**Key requirements:**
- ✅ Free to use, modify, and distribute
- ✅ Must keep source code open
- ✅ Must share modifications if you deploy as a web service
- ✅ Must retain copyright and attribution notices
- ❌ Cannot remove author attribution or rebrand

See [LICENSE](LICENSE) file for full AGPL terms.

### Commercial License

For proprietary/closed-source use without AGPL obligations, a [Commercial License](LICENSE-COMMERCIAL) is available.

**Benefits:**
- ✅ No source code disclosure requirements
- ✅ Integration into proprietary systems
- ✅ Priority support and updates
- ✅ Custom development assistance

**Contact for commercial licensing:** See [LICENSE-COMMERCIAL](LICENSE-COMMERCIAL) for details.

---

### Copyright & Attribution

```
Copyright (c) 2025 Timothy Kramer (KR8MER)
EAS Station - https://github.com/KR8MER/eas-station
```

**IMPORTANT:** All derivative works must retain attribution to the original author.
Rebranding or removing attribution is prohibited under both licenses.
See [NOTICE](NOTICE) file for complete terms.

### Why Dual Licensing?

- **For hobbyists & open-source**: Free to use under AGPL
- **For commercial use**: Option to license without copyleft obligations
- **For everyone**: Protects the author's rights and prevents unauthorized rebranding

## 🙏 Acknowledgments

- **NOAA/NWS** - Weather alert data and CAP specifications
- **FEMA/IPAWS** - National alert system integration
- **PostGIS Team** - Spatial database technology
- **Putnam County GIS Office** - Geographic boundary data (Greg Luersman, GIS Coordinator)
- **U.S. Census Bureau** - FIPS codes and TIGER/Line boundary data
- **Flask Community** - Web framework
- **RTL-SDR Project** - Software-defined radio tools
- **Amateur Radio Community** - Testing and feedback

## 📞 Resources

| Resource | Link |
|----------|------|
| **Documentation** | [docs/](docs/INDEX) |
| **NOAA CAP API** | https://www.weather.gov/documentation/services-web-api |
| **IPAWS** | https://www.fema.gov/emergency-managers/practitioners/integrated-public-alert-warning-system |
| **FCC Part 11** | https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-11 |
| **PostGIS** | https://postgis.net/documentation/ |

---

<div align="center">
  <strong>Made with ☕ and 📻 for Amateur Radio Emergency Communications</strong><br>
  <strong>73 de KR8MER</strong> 📡
</div>
