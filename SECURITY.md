# Security policy

For safety mode, which limits heating when a temperature sensor stops reporting, see [Advanced aspects](documentation/en/feature-advanced.md#safety-mode-operating-principle).

## Supported versions

Security fixes go into the latest release only. Before you report a problem, check that it still happens on the latest release.

## Report a vulnerability

Don't describe security problems in public issues, discussions, or forums.

1. Report the problem privately with [GitHub private vulnerability reporting](https://github.com/jmcollin78/versatile_thermostat/security/advisories/new).
2. If you can't use private reporting, start a [discussion](https://github.com/jmcollin78/versatile_thermostat/discussions) that asks the maintainer to contact you. Don't include any details about the problem.

In your report, include:

- The versions of Versatile Thermostat and Home Assistant that you use.
- The steps to reproduce the problem.
- What an attacker could do with it.

You'll get a reply in the advisory. If the advisory is published, it credits you unless you ask not to be credited.

### Security contacts

Private reports go to the maintainer, @jmcollin78. @jasonjhofmann helps triage them.

## Scope

Versatile Thermostat runs inside Home Assistant and controls heating and cooling through other Home Assistant entities. It has no cloud service and stores no account passwords. Most problems are ordinary bugs, so report them in public issues as usual.

Send a private report for problems that let someone without a Home Assistant login read or change a VTherm or its data. This includes the [vtherm_api](https://github.com/jmcollin78/vtherm_api) library that Versatile Thermostat uses.

Out of scope:

- Vulnerabilities in Home Assistant itself. Report them through the [Home Assistant security policy](https://www.home-assistant.io/security/).
- Attacks that need a Home Assistant login. Home Assistant's policy treats every logged-in user as trusted.
- Vulnerabilities in the devices and integrations that a VTherm controls. Report them to those projects.
- Vulnerabilities in third-party libraries. Report them to that library's maintainers.
