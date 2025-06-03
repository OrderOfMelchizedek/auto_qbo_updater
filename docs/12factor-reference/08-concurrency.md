# Factor VIII: Concurrency

**Principle:** Scale out via the process model

## Summary

Applications should scale horizontally by running multiple processes. Different types of work should be handled by different process types, and scaling happens by adding more processes, not by making processes larger.

## Key Concepts

- **Process Types**: Different processes for different workloads (web, worker, scheduler)
- **Horizontal Scaling**: Add more processes, not bigger processes
- **Process Formation**: The mix of process types and quantities
- **First-class Processes**: Processes are the primary unit of scaling

## The Unix Process Model

Inspired by Unix daemons:
- Each process does one thing well
- Processes are stateless and share-nothing
- Communication happens through standard protocols
- Process lifecycle managed by the system

## Process Types Examples

- **Web Process**: Handles HTTP requests
- **Worker Process**: Processes background jobs
- **Clock Process**: Runs scheduled tasks
- **Email Process**: Sends emails
- **Data Process**: ETL or data processing

## Scaling Strategies

### Vertical Scaling (LIMITED)
- Adding threads within a process
- Using async/event-driven models
- Has upper limits based on VM size

### Horizontal Scaling (PREFERRED)
- Running multiple process instances
- Distribution across multiple machines
- No theoretical upper limit
- Simple and reliable

## Process Management

### Don't Do This:
- Write PID files
- Daemonize processes
- Manage process lifecycle internally

### Do This:
- Let the platform manage processes
- Use process managers (systemd, Kubernetes, Heroku)
- Output to stdout/stderr
- Gracefully handle shutdown signals

## Benefits

1. **Simple Scaling**: Just run more processes
2. **Fault Isolation**: One crashed process doesn't affect others
3. **Resource Efficiency**: Right-sized processes for each workload
4. **Flexibility**: Easy to adjust process mix

## Example Process Formation

```
web: 3 processes
worker: 5 processes  
clock: 1 process
```

Scale by adjusting numbers:
```
web: 10 processes (handle more traffic)
worker: 20 processes (handle more jobs)
clock: 1 process (still just one scheduler)
```

## Original Source

For the complete explanation and examples, visit: https://12factor.net/concurrency
