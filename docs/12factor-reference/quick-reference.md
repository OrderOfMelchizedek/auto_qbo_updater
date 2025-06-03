# The Twelve-Factor App - Quick Reference

## Quick Summary of All 12 Factors

1. **Codebase** - One codebase tracked in revision control, many deploys
2. **Dependencies** - Explicitly declare and isolate dependencies
3. **Config** - Store config in the environment
4. **Backing services** - Treat backing services as attached resources
5. **Build, release, run** - Strictly separate build and run stages
6. **Processes** - Execute the app as one or more stateless processes
7. **Port binding** - Export services via port binding
8. **Concurrency** - Scale out via the process model
9. **Disposability** - Maximize robustness with fast startup and graceful shutdown
10. **Dev/prod parity** - Keep development, staging, and production as similar as possible
11. **Logs** - Treat logs as event streams
12. **Admin processes** - Run admin/management tasks as one-off processes

## One-Line Reminders

- **Codebase**: One repo, multiple deploys
- **Dependencies**: Declare everything, assume nothing
- **Config**: Environment variables only
- **Backing services**: Swappable via config
- **Build, release, run**: Immutable releases
- **Processes**: Stateless and share-nothing
- **Port binding**: Self-contained web server
- **Concurrency**: Scale horizontally with processes
- **Disposability**: Start fast, shutdown gracefully
- **Dev/prod parity**: Same tools everywhere
- **Logs**: Write to stdout only
- **Admin processes**: Same environment as app

## Key Principles

### For Development
- Explicit dependencies
- Environment-based config
- Same services as production
- stdout logging
- Fast startup

### For Deployment
- Immutable builds
- Horizontal scaling
- Stateless processes
- Graceful shutdown
- Platform manages logs

### For Operations
- Treat services as attachable resources
- Process model for scaling
- No differences between environments
- One-off tasks in same environment

## Common Anti-patterns to Avoid

1. ❌ Multiple codebases for one app
2. ❌ System dependencies
3. ❌ Config files in repo
4. ❌ Hardcoded service locations
5. ❌ Runtime code changes
6. ❌ Local file storage
7. ❌ External web server required
8. ❌ Vertical scaling only
9. ❌ Slow startup
10. ❌ Different dev/prod services
11. ❌ Writing to log files
12. ❌ Separate admin apps

## Benefits When Followed

- **Scalability**: Easy horizontal scaling
- **Portability**: Runs anywhere
- **Maintainability**: Clear separation of concerns
- **Reliability**: Fault-tolerant design
- **Agility**: Fast deployments and rollbacks
- **Simplicity**: Reduced operational complexity

---

For detailed explanations of each factor, see the individual markdown files in this directory or visit https://12factor.net/
