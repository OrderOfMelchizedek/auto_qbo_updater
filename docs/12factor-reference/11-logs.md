# Factor XI: Logs

**Principle:** Treat logs as event streams

## Summary

Applications should not manage log files or routing. Instead, they should write all output to stdout as an unbuffered stream, letting the execution environment handle collection, routing, and storage.

## Key Concepts

- **Event Streams**: Logs are continuous streams, not files
- **stdout Only**: Write all logs to standard output
- **No File Management**: Don't write to or rotate log files
- **Environment Routing**: Platform handles log aggregation

## What Are Logs?

- Time-ordered stream of events
- Text format (typically one event per line)
- Continuous flow while app runs
- Aggregated from all processes and services

## The Twelve-Factor Way

### Don't Do This:
```
❌ Write to log files
❌ Implement log rotation
❌ Manage log directories
❌ Build custom logging infrastructure
```

### Do This:
```
✅ Print to stdout/stderr
✅ Use simple print/console statements
✅ Let platform handle routing
✅ Keep logging code simple
```

## Benefits

1. **Simplicity**: No complex logging code
2. **Flexibility**: Logs can be routed anywhere
3. **Consistency**: Same approach in all environments
4. **Real-time**: Can tail logs live
5. **Integration**: Easy to connect to log services

## Execution Environment Responsibilities

The platform handles:
- Capturing output from all processes
- Collating multiple streams
- Routing to destinations
- Long-term storage
- Log rotation and retention

## Log Destinations

Platforms can route logs to:
- Files (for development)
- Terminal output (for debugging)
- Log aggregation services (Splunk, ELK)
- Data warehouses (for analysis)
- Monitoring systems (for alerts)

## Use Cases

### Development
```bash
$ npm start
[timestamp] Server starting...
[timestamp] Listening on port 3000
[timestamp] Request: GET /users
```

### Production
- Stream to centralized logging
- Search historical events
- Create dashboards and graphs
- Set up alerts and monitoring

## Best Practices

1. **Structured Logging**: Use consistent formats (JSON, key-value)
2. **Meaningful Messages**: Include context and relevant data
3. **Appropriate Levels**: Use debug, info, warn, error appropriately
4. **No Sensitive Data**: Never log passwords, tokens, or PII
5. **Correlation IDs**: Track requests across services

## Example Implementation

```javascript
// Simple and correct
console.log(`Request received: ${method} ${path}`);
console.error(`Database connection failed: ${error.message}`);

// Not twelve-factor
const fs = require('fs');
fs.appendFileSync('/var/log/app.log', logMessage); // ❌
```

## Original Source

For the complete explanation and examples, visit: https://12factor.net/logs
