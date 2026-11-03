# OpenTruck Code Signing Policy

This document is the code signing policy for the OpenTruck project. It is
referenced from the project's home page and from every signed release.

## Project and license

OpenTruck is a free, open-source heavy-duty diagnostics tool. It is licensed
under the **GNU General Public License, version 3 or (at your option) any
later version (GPL-3.0-or-later)**. There is **no dual licensing** and no
commercial/proprietary tier. The full license is in [`LICENSE`](LICENSE).

## What gets signed

Every Windows executable published in a release is signed:

* `OpenTruck.exe` — the main application
* `OpenTruckBridge32.exe` — the bundled 32-bit helper used to drive 32-bit-only
  RP1210 adapter drivers
* `OpenTruckSetup-<version>.exe` — the Inno Setup installer

## How binaries are built and signed

* Builds are produced **from the public repository's source code** on
  **Microsoft-hosted GitHub Actions Windows runners** (a fresh checkout, no
  pre-built artifacts), so the result is reproducible from source.
* Signing is performed by **SignPath Foundation** using its own code signing
  certificate, whose private key is generated and stored on a **hardware
  security module (HSM)**. The signed binaries therefore carry SignPath
  Foundation as the publisher.
* No private key, certificate, or password is ever stored on GitHub, in a CI
  runner, or on a maintainer's machine.
* Each signing request is **manually approved by a project maintainer** before
  the binary is signed.

## What is deliberately NOT signed / not shipped

* We do not sign, bundle, or redistribute third-party executables we did not
  build from our own source. If a signed upstream binary is ever needed, the
  upstream project is asked to sign it themselves.
* No malware, potentially unwanted programs, or security/vulnerability tools.

## Privacy and update checking

OpenTruck can check for new versions by querying the **public GitHub Releases
API** for this project. This happens two ways:

1. `Help ▸ Check for Updates` — a manual check the user triggers.
2. A silent on-startup check, which only surfaces a notice when a newer
   release actually exists.

These checks are a single HTTPS request to GitHub's public releases endpoint
for this repository. **No personal data, usage telemetry, or identifying
information is collected, transmitted, or stored.** The program has no other
network activity. There is no tracking, no analytics, and no phone-home other
than the update check described above.

The **on-startup** check can be turned off in *Preferences > Updates*
(the *Help > Check for Updates* item always works). It is on by default.

## Integrity

* A **SHA-256 checksum** is published alongside each release so a downloader
  can verify they received the exact signed file.
* Release notes describe what changed in each version.

## Contact

Project and maintainer information is on the repository's home page.
