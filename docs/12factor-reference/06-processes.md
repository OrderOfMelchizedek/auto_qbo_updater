# Factor VI: Processes

**Principle:** Execute the app as one or more stateless processes

## Summary

Applications should run as stateless processes that share nothing. Any persistent data must be stored in external backing services, not in process memory or local filesystem.

## Key Concepts

- **Stateless**: Processes don't store data between requests
- **Share-nothing**: No shared memory or filesystem between processes
- **Ephemeral Storage**: Local storage is temporary and transaction-scoped only
- **External State**: All persistent data lives in backing services

## What This Means

### Allowed (Temporary Use)
- Using memory/disk as a cache during a single transaction
- Downloading a file, processing it, and storing results in database
- Temporary files that are cleaned up after use

### Not Allowed
- Storing user session data in process memory
- Keeping application state on local filesystem
- Assuming files/data will exist between requests
- Using "sticky sessions" for load balancing

## Why Stateless?

1. **Scalability**: Can run multiple processes without coordination
2. **Resilience**: Process crashes don't lose user data
3. **Flexibility**: Processes can be started/stopped/moved freely
4. **Simplicity**: No complex state synchronization needed

## Common Violations

- Sticky sessions (routing users to same process)
- In-memory session storage
- Local file uploads without immediate processing
- Compiled assets stored on filesystem at runtime

## Proper State Storage

Store persistent data in:
- Databases (PostgreSQL, MySQL, MongoDB)
- Cache stores (Redis, Memcached)
- Object storage (S3, Cloud Storage)
- Session stores (Redis with expiration)

## Best Practices

- Compile assets during build stage, not runtime
- Use centralized session stores for user data
- Upload files directly to object storage
- Design for horizontal scaling from day one
- Assume any process can handle any request

## The Litmus Test

Can you kill any process at any time without losing user data? If not, you're storing state incorrectly.

## Original Source

For the complete explanation and examples, visit: https://12factor.net/processes
