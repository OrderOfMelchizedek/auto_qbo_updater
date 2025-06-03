# Factor VII: Port Binding

**Principle:** Export services via port binding

## Summary

Apps should be completely self-contained and export services by binding to a port. They shouldn't rely on runtime injection of a webserver, but instead should include the webserver library as a dependency.

## Key Concepts

- **Self-contained**: App includes its own webserver
- **Port Binding**: App listens on a specific port for requests
- **No Container Dependency**: Doesn't require Apache, IIS, or Tomcat
- **Protocol Agnostic**: Works for HTTP, XMPP, Redis protocol, etc.

## How It Works

1. App declares webserver as a dependency
2. App starts and binds to a port (e.g., 5000)
3. App listens for incoming requests on that port
4. Routing layer directs traffic to the app's port

## Examples by Language

- **Python**: Flask, Django with Gunicorn, Tornado
- **Ruby**: Sinatra/Rails with Thin, Puma, or Unicorn
- **Node.js**: Express with built-in HTTP server
- **Java**: Embedded Jetty or Tomcat
- **Go**: Built-in net/http package

## Benefits

- **Simplicity**: One less moving part in production
- **Portability**: Runs the same way everywhere
- **Development/Production Parity**: Same server in all environments
- **Microservices Ready**: Apps can serve as backing services to each other

## Implementation

```
# Development
App binds to localhost:5000
Developer accesses http://localhost:5000

# Production
App binds to 0.0.0.0:$PORT
Router/Load balancer forwards traffic to app instances
```

## Not Just for Web Apps

Port binding works for any network service:
- Web applications (HTTP/HTTPS)
- WebSocket servers
- API services
- Message brokers
- Cache servers
- Any TCP/UDP service

## Apps as Backing Services

With port binding, your app can become a backing service for other apps. Just provide the URL as configuration to consuming apps.

## Anti-patterns to Avoid

- Requiring Apache/Nginx modules
- Depending on application servers like Tomcat
- Assuming a specific web server environment
- Hardcoding ports instead of using configuration

## Original Source

For the complete explanation and examples, visit: https://12factor.net/port-binding
