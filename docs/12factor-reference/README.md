# The Twelve-Factor App Reference Guide

This is a reference guide to the Twelve-Factor App methodology for building modern, scalable, maintainable software-as-a-service applications.

**Original Source:** https://12factor.net/

## Overview

The twelve-factor methodology provides best practices for:
- Building apps that are easy to deploy and scale
- Minimizing divergence between development and production
- Enabling continuous deployment
- Maintaining clean contracts with the operating system

## The 12 Factors

1. **[Codebase](https://12factor.net/codebase)** - One codebase tracked in revision control, many deploys
2. **[Dependencies](https://12factor.net/dependencies)** - Explicitly declare and isolate dependencies
3. **[Config](https://12factor.net/config)** - Store config in the environment
4. **[Backing services](https://12factor.net/backing-services)** - Treat backing services as attached resources
5. **[Build, release, run](https://12factor.net/build-release-run)** - Strictly separate build and run stages
6. **[Processes](https://12factor.net/processes)** - Execute the app as one or more stateless processes
7. **[Port binding](https://12factor.net/port-binding)** - Export services via port binding
8. **[Concurrency](https://12factor.net/concurrency)** - Scale out via the process model
9. **[Disposability](https://12factor.net/disposability)** - Maximize robustness with fast startup and graceful shutdown
10. **[Dev/prod parity](https://12factor.net/dev-prod-parity)** - Keep development, staging, and production as similar as possible
11. **[Logs](https://12factor.net/logs)** - Treat logs as event streams
12. **[Admin processes](https://12factor.net/admin-processes)** - Run admin/management tasks as one-off processes

## About This Reference

This reference guide provides summaries and key concepts for each factor. For the complete methodology and detailed explanations, please visit the original source at https://12factor.net/

Created on: 2025-06-01
