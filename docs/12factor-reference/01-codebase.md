# Factor I: Codebase

**Principle:** One codebase tracked in revision control, many deploys

## Summary

This factor establishes the fundamental relationship between code and deployments. Each application should have exactly one codebase that is tracked in version control (like Git, Mercurial, or Subversion).

## Key Concepts

- **Single Source of Truth**: One codebase serves as the authoritative source for the application
- **Multiple Deployments**: The same codebase can be deployed to multiple environments (development, staging, production)
- **Version Control**: All code must be tracked in a version control system
- **No Code Duplication**: Shared code should be extracted into libraries, not copied between apps

## Important Points

1. If you have multiple codebases, you have a distributed system (not a single app)
2. Each deployment may run different versions/commits of the codebase
3. All deployments (dev, staging, prod) share the same codebase
4. Shared code belongs in libraries managed through dependency systems

## Anti-patterns to Avoid

- Multiple apps sharing the same codebase
- Code not tracked in version control
- Different codebases for different environments

## Original Source

For the complete explanation and examples, visit: https://12factor.net/codebase
