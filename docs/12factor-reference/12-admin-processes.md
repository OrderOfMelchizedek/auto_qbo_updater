# Factor XII: Admin Processes

**Principle:** Run admin/management tasks as one-off processes

## Summary

Administrative tasks should run as one-off processes in the same environment as regular app processes, using the same code, config, and dependencies. They should not be special cases or separate systems.

## Key Concepts

- **Same Environment**: Admin tasks run in identical setup as app
- **One-off Execution**: Not part of the regular process formation
- **Same Release**: Use the same code and config version
- **Proper Isolation**: Use same dependency management

## Common Admin Processes

### Database Operations
- Migrations: `rails db:migrate`, `manage.py migrate`
- Schema updates
- Data fixes and cleanups

### Interactive Consoles
- REPL shells for debugging
- Model inspection
- Live data queries
- Testing code snippets

### Maintenance Scripts
- Data imports/exports
- Report generation
- Cleanup tasks
- System health checks

## Implementation Rules

1. **Use Same Codebase**
   - Admin code ships with app code
   - No separate admin repositories
   - Version controlled together

2. **Use Same Dependencies**
   - Same isolation tools (bundler, virtualenv)
   - Same library versions
   - No special admin dependencies

3. **Use Same Config**
   - Same environment variables
   - Same backing services
   - Same connection strings

## Examples by Platform

### Local Development
```bash
# Ruby
bundle exec rails console
bundle exec rake task:name

# Python
python manage.py shell
python scripts/maintenance.py

# Node.js
npm run console
node scripts/migrate.js
```

### Production
```bash
# Heroku
heroku run rails console
heroku run python manage.py migrate

# Kubernetes
kubectl exec -it pod-name -- rails console
kubectl run --rm -i --tty admin-pod --image=app:latest -- python manage.py shell

# SSH
ssh server 'cd /app && bundle exec rake task:name'
```

## Best Practices

1. **Keep Scripts Simple**: One-off tasks should be focused
2. **Use Frameworks**: Leverage built-in console/task systems
3. **Log Output**: Admin processes should log like regular processes
4. **Handle Errors**: Proper error handling and rollback
5. **Document Tasks**: Clear documentation for admin procedures

## Anti-patterns to Avoid

- Separate admin applications
- Different dependency versions for admin tasks
- Manual server modifications
- Unversioned admin scripts
- Special admin configurations

## Why This Matters

- **Consistency**: Same behavior in all environments
- **Reliability**: No sync issues between admin and app code
- **Simplicity**: One codebase to maintain
- **Safety**: Tested code, proper isolation

## REPL Preference

Twelve-factor favors languages with good REPL support:
- Immediate feedback
- Interactive debugging
- Easy experimentation
- Quick fixes

Languages with great REPLs: Ruby (irb), Python, Node.js, Clojure, Elixir

## Original Source

For the complete explanation and examples, visit: https://12factor.net/admin-processes
