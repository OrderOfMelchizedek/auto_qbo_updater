# Factor III: Config

**Principle:** Store config in the environment

## Summary

Configuration that varies between deployments should be stored in environment variables, not in code. This ensures strict separation between code and config, making applications more secure and portable.

## Key Concepts

- **Environment Variables**: Store all deployment-specific config in env vars
- **Strict Separation**: Keep config completely separate from code
- **No Config Files**: Avoid language-specific config files that might be accidentally committed
- **Granular Control**: Each config value is independent, not grouped into "environments"

## What Counts as Config?

**Config includes:**
- Database URLs and credentials
- API keys for external services
- Hostnames and ports
- Feature flags per deployment

**NOT config:**
- Internal application settings (routes, module connections)
- Business logic
- Code structure

## The Litmus Test

Could you make your codebase open source right now without compromising any credentials? If not, you have config in your code.

## Why Environment Variables?

1. Language and OS agnostic
2. Easy to change between deploys
3. Can't be accidentally committed to version control
4. Simple to manage in deployment systems
5. Scales cleanly as deployments grow

## Anti-patterns to Avoid

- Hardcoded values in code
- Config files in version control
- Grouped "environment" files (dev.yml, prod.yml)
- Language-specific config mechanisms

## Best Practices

- Keep env var names consistent and descriptive
- Document required env vars
- Provide sensible defaults where appropriate
- Validate config on app startup

## Original Source

For the complete explanation and examples, visit: https://12factor.net/config
