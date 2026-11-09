# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## GitHub is used for everything

GitHub is used to host code, track issues and feature requests, and accept pull requests.

Pull requests (PRs) are a great way to propose changes to the codebase. Throughout its history, the Versatile Thermostat team has accepted many PRs, and these contributions have played a significant part in the project's success. We are very grateful to the entire community for its contributions.

## How PRs are reviewed

With the rise of AI tools, almost everyone can now prepare a PR. Some are high quality and get merged; others cannot be accepted.

The number of PRs has grown significantly. Reviews are mostly manual and focus on two main points:

- the quality of the proposed solution;
- its consistency with the future direction and vision of Versatile Thermostat.

A PR addressing a very specific need, such as a device behaving differently from what VTherm expects or a user's particular way of using the integration, cannot necessarily be accepted. In particular, if it increases complexity and introduces risk for other users, its benefits must be weighed against those consequences.

It is no longer possible to review every incoming PR in detail. We therefore have to triage them and prioritize those that bring real value to the product or the community.

Since 2025, a mechanism has allowed anyone to develop features without changing the Versatile Thermostat integration or putting other users at risk: plugins. They are built on the [`vtherm_api`](https://github.com/jmcollin78/vtherm_api) module.

Before proposing a PR, please consider whether your need could instead be addressed by a plugin that only the users concerned would install.

If you are unsure whether a change is appropriate or likely to be accepted, contact the maintainer before starting development. This allows the proposed approach to be discussed early.

A rejected PR can be disappointing, but the decision is not personal: it is intended to protect the integration and the experience of all users. Thank you for your understanding.

## Proposing a change

1. Fork the repo and create your branch from `master`.
2. If you've changed something, update the documentation.
3. Make sure your code is formatted with Black.
4. Test your contribution.
5. Submit your PR.

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using GitHub's [issues](../../issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](../../issues/new/choose).

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People *love* thorough bug reports. I'm not even kidding.

## Use a Consistent Coding Style

Use [black](https://github.com/ambv/black) to make sure the code follows the style.

## Test your code modification

This custom component follows the best practices described in the [integration blueprint](https://github.com/custom-components/integration_blueprint).

It comes with development environment in a container, easy to launch
if you use Visual Studio Code. This container runs a standalone Home Assistant
instance, already configured with the included
[`.devcontainer/configuration.yaml`](./.devcontainer/configuration.yaml) file.

## License

By contributing, you agree that your contributions will be licensed under its MIT License.