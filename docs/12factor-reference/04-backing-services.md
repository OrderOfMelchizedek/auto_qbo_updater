# Factor IV: Backing Services

**Principle:** Treat backing services as attached resources

## Summary

Backing services are any services your app uses over the network. The app should treat all backing services as attached resources that can be swapped out without code changes, whether they're managed locally or by third parties.

## Key Concepts

- **Attached Resources**: Services connected via network that can be attached/detached at will
- **No Code Distinction**: Local vs third-party services look identical to the app
- **Configuration-based**: Service locations and credentials stored in config
- **Loose Coupling**: Services can be swapped without modifying application code

## Examples of Backing Services

- **Databases**: MySQL, PostgreSQL, MongoDB, CouchDB
- **Message Queues**: RabbitMQ, Beanstalkd, Amazon SQS
- **Cache Systems**: Redis, Memcached
- **Email Services**: SMTP servers, SendGrid, Postmark
- **File Storage**: Local filesystem, Amazon S3, Google Cloud Storage
- **External APIs**: Payment gateways, social media APIs, mapping services

## Implementation

1. Access all services through URLs/connection strings in config
2. Use standard interfaces (e.g., database drivers) that work with multiple providers
3. Design code to be agnostic about service location
4. Handle service failures gracefully

## Benefits

- **Flexibility**: Easily switch between providers
- **Scalability**: Add or remove service instances as needed
- **Disaster Recovery**: Quickly swap failed services
- **Development/Production Parity**: Use same service types across environments

## Example Scenarios

- Switching from local MySQL to Amazon RDS
- Replacing self-hosted email server with SendGrid
- Moving from filesystem storage to S3
- Changing from one Redis provider to another

All these changes require only config updates, not code changes.

## Original Source

For the complete explanation and examples, visit: https://12factor.net/backing-services
