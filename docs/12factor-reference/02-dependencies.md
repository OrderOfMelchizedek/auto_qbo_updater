# Factor II: Dependencies

**Principle:** Explicitly declare and isolate dependencies

## Summary

Applications must explicitly declare all dependencies and use isolation tools to ensure no system dependencies leak into the app. This creates reproducible builds and simplifies setup for new developers.

## Key Concepts

- **Explicit Declaration**: All dependencies must be declared in a manifest file
- **Dependency Isolation**: Use tools to ensure the app uses only declared dependencies
- **No System Dependencies**: Never rely on system-wide packages or tools
- **Reproducible Builds**: Any developer should be able to set up the app with a simple command

## Implementation Examples

Different languages use different tools:
- **Ruby**: Gemfile (declaration) + bundle exec (isolation)
- **Python**: requirements.txt/Pipfile (declaration) + virtualenv/venv (isolation)
- **Node.js**: package.json (declaration) + npm/yarn (isolation)
- **Java**: pom.xml/build.gradle (declaration) + Maven/Gradle (isolation)

## Important Points

1. Both declaration AND isolation are required - one without the other is insufficient
2. System tools (like curl, ImageMagick) should be vendored if needed
3. Simplifies onboarding - new developers only need runtime and dependency manager
4. Ensures consistency across all environments

## Benefits

- Predictable, reproducible builds
- Easy setup for new team members
- No surprises from system-level changes
- Clear documentation of what the app needs to run

## Original Source

For the complete explanation and examples, visit: https://12factor.net/dependencies
