# Factor V: Build, Release, Run

**Principle:** Strictly separate build and run stages

## Summary

The deployment pipeline must have three distinct, separate stages: build (compile code), release (combine build with config), and run (execute in production). This separation ensures reliability and enables rollbacks.

## The Three Stages

### 1. Build Stage
- Converts source code into an executable bundle
- Fetches and vendors dependencies
- Compiles code and assets
- Produces a build artifact
- Can be complex - errors happen when developers are present

### 2. Release Stage
- Combines build artifact with environment config
- Creates an immutable, uniquely identified release
- Ready for immediate execution
- Stored for potential rollback

### 3. Run Stage
- Executes the release in the production environment
- Launches app processes
- Should be as simple as possible
- May happen automatically (restarts, scaling)

## Key Principles

- **One-way Flow**: Code → Build → Release → Run (never backwards)
- **Immutable Releases**: Once created, a release cannot be modified
- **Unique Identification**: Every release has a unique ID (timestamp or version)
- **Append-only**: New changes create new releases, not modify existing ones

## Benefits

1. **Rollback Capability**: Easy to revert to previous releases
2. **Audit Trail**: Clear history of what was deployed when
3. **Consistency**: Same build can be released to multiple environments
4. **Reliability**: Simple run stage reduces runtime failures

## Implementation Tips

- Automate the build process (CI/CD)
- Store releases with clear identifiers
- Keep the run stage minimal - just process launching
- Use release management tools for easy rollbacks
- Never allow runtime code modifications

## Why This Matters

- Problems at runtime often happen when developers aren't available
- Complex runtime operations increase failure risk
- Clear separation enables better tooling and automation
- Immutable releases ensure reproducible deployments

## Original Source

For the complete explanation and examples, visit: https://12factor.net/build-release-run
