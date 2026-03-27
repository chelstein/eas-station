# ⚖️ Terms of Use

_Last updated: February 14, 2026_

> **Critical Safety Notice:** EAS Station is experimental software. It must not be used for life-safety, mission-critical, or FCC-mandated alerting. Commercially certified EAS equipment remains the only acceptable solution for regulatory compliance.

## 1. Project Status & Intended Use
- EAS Station is a community-driven development project currently in a pre-production, experimental phase with a roadmap focused on matching the functionality of commercial encoder/decoder hardware using off-the-shelf components.
- The reference build now leverages Raspberry Pi 5 compute modules (4 GB RAM baseline) paired with GPIO relay HATs, RS-232 interfaces, SDR receivers, and broadcast-grade audio cards. Raspberry Pi 4 hardware remains compatible for lab work, but it is no longer the documented baseline. None of these components are an approved substitute for certified encoder/decoder equipment until the software attains formal authorization.
- The codebase has been cross-checked against open-source utilities such as [multimon-ng](https://github.com/EliasOenal/multimon-ng) for decoder parity. All other logic, workflows, and documentation are original contributions from the project maintainers.
- The software is provided strictly for research, testing, and educational exploration. It is **not** a replacement for FCC-certified Emergency Alert System hardware or services and must not be relied upon for life or property protection.

## 2. No Production Deployment or Warranties
- The platform is **not** ready for production use. No representations or warranties are made about the accuracy, completeness, reliability, availability, or timeliness of the system.
- All outputs—including audio files, logs, dashboards, and reports—may contain defects or omissions. Field validation and regulatory certification have **not** been completed.
- You assume all risk for evaluating the software in lab or demonstration environments. The project is provided strictly on an “AS IS” basis without warranties of any kind.

## 3. Disclaimer of Liability & Indemnification
- The authors, maintainers, and contributors disclaim any and all liability—civil, criminal, and regulatory—for damages, injuries, penalties, data loss, downtime, enforcement actions, or criminal proceedings that may arise from use or misuse of EAS Station—including malicious, unauthorized, or noncompliant uses by you or anyone who gains access to your deployment.
- **The developer and contributors of this project bear absolutely no responsibility for any criminal activity conducted using this software.**
- No emergency responses, broadcast activations, or public warning decisions should be based on this project. Use at your own risk.
- You agree to indemnify, defend, and hold harmless the project authors, maintainers, and contributors from any and all claims, demands, damages, losses, costs, and liabilities—including attorneys' fees and criminal defense costs—arising out of your deployment, configuration, redistribution, or failure to control access to the project.

## 4. Acceptable Use & Prohibited Activities
- Operate the software only in controlled, non-production lab or development environments.
- Do not present generated outputs as official alerts or public information.
- Do not connect EAS Station directly to transmitter plants, IPAWS live interfaces, dispatch systems, or any life-safety infrastructure.
- Do not use the project to transmit, relay, spoof, or interfere with authorized public warning systems or licensed broadcast facilities.
- Do not use the project for any malicious, unlawful, deceptive, surveillance, harassment, or disruptive purpose—including denial of service, spoofing, jamming, or unauthorized interception of communications.
- You are solely responsible for restricting access to your deployment and for any downstream impacts caused by third parties who use, repurpose, or chain this software into other tools.
- Retain attribution to the project and respect the licenses of any incorporated open-source dependencies.

## 4a. Criminal Liability & Federal Law Violations

> ⚠️ **Criminal Warning:** Misuse of this software may constitute one or more felonies under federal law and the laws of multiple states and jurisdictions. Ignorance of these laws is not a defense.

Misuse of EAS Station—including unauthorized broadcast, spoofing, or interference with public warning systems—may constitute serious criminal offenses under United States federal law and the laws of multiple states and jurisdictions worldwide. You acknowledge and agree that:

- **Unauthorized transmission of false Emergency Alert System signals** is a federal crime under **18 U.S.C. § 1038** (False Information and Hoaxes), punishable by up to five (5) years imprisonment per offense, plus civil penalties and restitution, for each broadcast that elicits or is likely to elicit an emergency response.
- **Willful interference with authorized Emergency Alert System broadcasts** may violate **47 U.S.C. § 325** and **47 U.S.C. § 333**, and related provisions of the Communications Act of 1934 (as amended), subject to fines of up to $100,000 per violation per day under 47 U.S.C. § 503(b), criminal prosecution under **47 U.S.C. § 501**, and forfeiture of equipment.
- **Transmission of false distress signals** is a criminal offense under **47 U.S.C. § 325(a)**, subject to criminal fines and imprisonment.
- **State and local laws** in virtually all U.S. jurisdictions impose additional criminal penalties—including felony charges—for false emergency alerts, false fire alarms, or interference with emergency communications systems. Criminal charges from multiple jurisdictions may be pursued simultaneously for a single act of misuse.
- In jurisdictions outside the United States, equivalent or more severe criminal statutes may apply, and international law enforcement cooperation may result in prosecution across borders.
- **The developer, maintainers, and contributors of EAS Station bear absolutely no criminal, civil, or regulatory liability for any act, omission, or crime committed by any person using this software.** Your use of this software constitutes your sole and exclusive acceptance of all criminal, civil, and regulatory risk and liability arising from that use.
- The project authors are not accomplices, aiders, or abettors of any misuse and explicitly disclaim any knowledge of, participation in, or responsibility for any illegal activity conducted using this software. The existence of this software does not constitute authorization, endorsement, or facilitation of any unlawful act.

## 4b. Documented Real-World Enforcement Cases

> EAS Station generates **valid**, standards-compliant SAME-encoded audio that has been confirmed by testing across multiple receivers to activate ENDEC hardware and software relay equipment—exactly as a live alert would. The cases below are real documented enforcement actions that arose from exactly this type of signal. They are directly applicable to any output produced by this software.

### Case 1 — iHeartMedia / *The Bobby Bones Show*, $1,000,000 Consent Decree (2015)

iHeartMedia aired counterfeit EAS Attention Signals (the two-tone 853/960 Hz sequence) during *The Bobby Bones Show* on multiple iHeartMedia stations as part of a comedy segment. The signals were sufficiently well-formed to be intercepted as real alerts. The FCC's Enforcement Bureau initiated proceedings and iHeartMedia entered into a **Consent Decree (FCC DA 15-199)** requiring payment of a **$1,000,000 civil penalty**, adoption of a mandatory EAS compliance program, and multi-year reporting to the FCC. The decree explicitly states that broadcasting EAS tones outside authorized emergency or test use violates 47 C.F.R. § 11.45 regardless of intent.

Source: FCC DA 15-199 — <https://docs.fcc.gov/public/attachments/DA-15-199A1.pdf>

### Case 2 — *Olympus Has Fallen* Movie Trailer, $1,900,000 Multi-Network Settlement (2014)

A theatrical trailer for the film *Olympus Has Fallen* contained EAS Attention Signals and was aired across multiple national broadcast and cable networks. The signals activated receiving equipment and constituted an unauthorized transmission under 47 C.F.R. § 11.45. The FCC issued Notices of Apparent Liability to the networks involved; the proceedings concluded in a combined **settlement of $1,900,000 (FCC DA 14-1097)** across the multiple licensees. This case established that unauthorized EAS signal transmission liability attaches to *every entity* in the distribution chain—not only the original content producer.

Source: FCC DA 14-1097 — <https://docs.fcc.gov/public/attachments/DA-14-1097A1.pdf>

### Case 3 — Montana "Zombie Apocalypse" EAS Cascade Hack (January 11, 2013)

Attackers gained unauthorized access to EAS encoder/decoder hardware at KRTV-TV (Great Falls, MT) and KXLH (Helena, MT) and injected a fabricated SAME-encoded alert stating: *"Civil authorities in your area have reported that the bodies of the dead are rising from their graves and attacking the living."* Because the injected SAME headers were correctly formatted and encoded at the proper bit rate, receiving equipment throughout the Montana EAS relay network **automatically re-broadcast the message** without further human action—demonstrating the inherent cascade behavior of the EAS relay system when presented with a conforming signal. The FCC issued Public Advisory **DA 13-108** warning all EAS Participants about equipment security vulnerabilities and opened enforcement proceedings against the affected stations. The incident is cited in FCC guidance as direct evidence that properly formatted EAS signals trigger automated relay with no human gate.

Source: FCC Public Advisory DA 13-108 — <https://docs.fcc.gov/public/attachments/DA-13-108A1.pdf>

### Case 4 — Ongoing FCC EAS Enforcement Pattern (2013–present)

Since 2013 the FCC Enforcement Bureau has entered into consent decrees and issued forfeiture orders against dozens of licensees for EAS tone misuse in advertisements, movie trailers, comedic content, podcasts, and streaming programming. Individual per-violation forfeitures have ranged from **$8,000 to $325,000**, and consent decree civil penalties have reached seven figures. Enforcement actions routinely include mandatory compliance programs, annual reporting obligations, and the possibility of license revocation under 47 U.S.C. § 312. All FCC enforcement records are publicly searchable at <https://www.fcc.gov/enforcement/orders>.

Applicable rules: 47 C.F.R. § 11.45 (prohibition on EAS code/Attention Signal use outside emergencies and tests); 47 U.S.C. § 503(b) (forfeiture authority up to $100,000/violation/day); 47 U.S.C. § 501 (criminal penalties up to $10,000 fine and 1 year imprisonment per violation).

## 5. Enforcement & Termination
- The maintainers reserve the right to revoke access to hosted resources, documentation, or support channels for any user who violates these terms or engages in malicious or unsafe activity.
- No right to continued access, updates, or support is granted. Your permission to use the software terminates immediately if you breach these terms.

## 6. Data Handling, Privacy, and Logging
- The project is not designed to store protected personal information. Avoid ingesting sensitive or regulated data. If you choose to process such data, you are solely responsible for implementing appropriate safeguards and compliance controls.
- System logs, metrics, and audio captures may include time-stamped operational details. You are responsible for reviewing, redacting, or deleting this material before sharing it externally.
- No guarantee is made that encryption, access controls, or secure deletion mechanisms will meet your organizational or regulatory requirements.

## 7. Security Expectations
- You are responsible for securing any deployment, including network isolation, credential management, TLS termination, and operating system hardening.
- The maintainers do not warrant that the software is free of vulnerabilities. Promptly apply security updates, review dependency advisories, and perform your own penetration testing before exposing any component to untrusted networks.

## 8. External References & Third-Party Components
- Comparisons to third-party projects (e.g., multimon-ng) are for feature parity checks only. Those projects are governed by their respective licenses and are not endorsed by, nor affiliated with, EAS Station.
- Third-party libraries, firmware, container images, and hardware integrations are subject to their own licenses and warranties. You are responsible for reviewing and complying with those terms.

## 9. Licensing & Contributions
- The EAS Station source code is dual-licensed under the [GNU Affero General Public License v3 (AGPL-3.0)](../../LICENSE) for open-source use and a [Commercial License](../../LICENSE-COMMERCIAL) for proprietary use. Copyright remains with Timothy Kramer (KR8MER).
- By submitting code, documentation, or other content, contributors agree that their work is provided under the AGPL-3.0 license unless a separate commercial agreement is in place.
- All commits must include a Developer Certificate of Origin (DCO) sign-off line (`Signed-off-by`) affirming that the contributor has the right to submit the work under the project license. Instructions are provided in [CONTRIBUTING.md](../process/CONTRIBUTING).

## 10. Updates & Change Control
- These terms may change as the project evolves. Continued use of the repository or website after an update constitutes acceptance of the revised terms.
- Significant changes will be documented in the project changelog or release notes. Operators evaluating new builds must review the published changelog, confirm the version shown in the UI (sourced from the repository `VERSION` manifest), and verify that critical workflows (alert ingest, SAME generation, GPIO control, audio playout) still function before relying on the update for lab exercises.

## 11. Export, Compliance, and Local Regulations
- You are responsible for ensuring that your use, export, or re-export of the software complies with applicable laws, including U.S. export controls and the regulations of any destination country.
- If you integrate radio hardware, transmitters, or decoders, you must comply with all licensing, spectrum, and broadcast rules that apply in your jurisdiction.

## 12. Contact
- Questions about these terms can be directed through the GitHub issue tracker.
- Do **not** submit emergency requests, personal data, or public warning content through that channel.

## 13. AMPR Network (44.0.0.0/8) — Non-Commercial Use

This service may be accessible via the **AMPRNet** IPv4 address block (`44.0.0.0/8`), which is allocated globally to the licensed amateur radio community by the [Amateur Radio Digital Communications (ARDC)](https://www.ampr.org/) foundation and managed under amateur radio service rules (FCC 47 CFR Part 97 in the United States).

In accordance with FCC Part 97, ARDC allocation policy, and the terms governing the AMPRNet address space:

- **This service is strictly NON-COMMERCIAL.** No commercial activity, for-profit transactions, or commercial advertising of any kind is conducted through this AMPRNet-accessible endpoint.
- This deployment is operated by a licensed amateur radio operator (KR8MER) for non-commercial research, experimentation, and emergency communications training.
- Any use of this service via the 44.0.0.0/8 address space must remain consistent with FCC Part 97 non-commercial requirements.
- Commercial exploitation of the 44.0.0.0/8 block is prohibited under ARDC allocation policy and applicable FCC regulations.

For information on the AMPRNet allocation and acceptable use policy, see [ampr.org](https://www.ampr.org/).
For the FCC Part 97 rules governing amateur radio service, see [47 CFR Part 97](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-97).
