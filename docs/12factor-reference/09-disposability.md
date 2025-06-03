# Factor IX: Disposability

**Principle:** Maximize robustness with fast startup and graceful shutdown

## Summary

Processes should be disposable - they can be started or stopped instantly. This requires fast startup times, graceful shutdown handling, and designing for sudden termination.

## Key Concepts

- **Fast Startup**: Processes ready in seconds, not minutes
- **Graceful Shutdown**: Clean handling of SIGTERM signals
- **Crash Resilience**: Robust against sudden process death
- **Disposable**: Processes can be created/destroyed freely

## Fast Startup

### Why It Matters
- Enables rapid scaling
- Faster deployments
- Quick recovery from failures
- Better resource utilization

### Best Practices
- Minimize initialization work
- Lazy-load when possible
- Pre-compile assets in build stage
- Keep dependencies lightweight

## Graceful Shutdown

### Web Processes
1. Stop accepting new connections
2. Complete in-flight requests
3. Exit cleanly

### Worker Processes
1. Stop accepting new jobs
2. Complete current job or return to queue
3. Release any locks
4. Exit cleanly

## Handling SIGTERM

```
# Pseudo-code example
signal.on('SIGTERM', () => {
  server.close(() => {
    // Cleanup resources
    process.exit(0)
  })
})
```

## Robustness Strategies

### Make Operations Idempotent
- Jobs can be safely retried
- No side effects from repeated execution

### Use Transactions
- Wrap work in database transactions
- Rollback on failure

### Implement Timeouts
- Don't let requests run forever
- Set reasonable time limits

### Queue Design
- Use robust queuing systems
- Automatic job return on disconnect
- At-least-once delivery guarantees

## Anti-patterns to Avoid

- Long startup sequences
- Ignoring shutdown signals
- Assuming graceful shutdown always happens
- Non-idempotent operations
- Holding locks without timeouts

## The "Crash-Only" Philosophy

Design assuming:
- Processes will be killed without warning
- Hardware will fail
- Networks will partition
- Graceful shutdown is a bonus, not a guarantee

## Benefits

1. **Elasticity**: Scale up/down quickly
2. **Resilience**: Recover from failures fast
3. **Agility**: Deploy changes rapidly
4. **Efficiency**: Optimal resource usage

## Original Source

For the complete explanation and examples, visit: https://12factor.net/disposability
