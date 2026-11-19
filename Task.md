# Bimebazar Senior Backend Assignment: URL Shortener

## Purpose and scope

Build a URL-shortening service using Python and FastAPI. A client submits a long URL and receives a unique short code. Requests to the corresponding short URL redirect to the original URL. The service also records visits and exposes visit statistics.

This document translates the functional and non-functional requirements of `Senior Backend Task.pdf` into technical English. It does not prescribe solutions where the assignment leaves a design decision to the candidate.

The assignment emphasizes clear reasoning, code clarity, and explicit architectural trade-offs. The estimated implementation effort is 6–8 hours.

## 1. Functional requirements

### FR-01: Create a short URL

- Implement `POST /shorten` using FastAPI.
- Accept an original URL and return a short code.
- Reject invalid URLs.
- Ensure that each short code uniquely identifies a stored URL mapping.
- Handle collisions during short-code generation, including collisions caused by concurrent requests.

The request and response schemas, validation rules, error responses, and code-generation strategy must be defined by the implementation and documented where relevant.

### FR-02: Redirect to the original URL

- Implement `GET /{short_code}`.
- Resolve the short code to its stored original URL and return an HTTP redirect.
- Define the behavior for unknown short codes.

The redirect status code and unknown-code response are implementation decisions; the brief does not specify their exact values.

### FR-03: Retrieve visit statistics

- Implement `GET /stats/{short_code}`.
- Return the number of visits associated with the specified short code.
- Define the behavior for unknown short codes.

The implementation must define what constitutes a counted visit and document any delay between a redirect and its visibility in statistics.

### FR-04: Define URL lifecycle and repeated-submission behavior

- Define the lifecycle of a shortened URL.
- Explicitly choose and document whether repeated submissions of the same original URL return the same short code or create different short codes.
- Explain the trade-offs of the selected behavior.
- Ensure that the chosen behavior remains consistent under concurrent submissions.

The brief does not explicitly require expiration, deletion, custom aliases, or URL-management endpoints.

### FR-05: Persist URL mappings and visit information

- Use SQLAlchemy or SQLModel for database access.
- Design a schema containing at least:
  - `original_url`
  - `short_code`
  - `created_at`
  - A visit count or a separate visit-log table.
- Use Alembic to define database migrations.

The database engine and the storage mechanism for IP/timestamp logs are implementation decisions. Both visit statistics and visit logging must be supported.

### FR-06: Log visits through reusable infrastructure

- Record the client IP address and timestamp when a short URL is opened.
- Implement visit logging using a decorator or middleware.
- Avoid duplicating visit-logging logic inside endpoint handlers.
- Explain alternative approaches to analytics collection in the documentation.

## 2. Non-functional requirements

### NFR-01: Concurrency and data integrity

The service must handle both of the following scenarios correctly:

1. Concurrent requests attempt to create the same short code.
2. Many concurrent requests visit the same short URL.

The implementation and its documentation must address:

- Database uniqueness constraints.
- Concurrent inserts and short-code collisions.
- Transaction boundaries and transaction isolation.
- Atomic updates and counter increments, where applicable.
- Prevention of lost updates and incorrect visit counts.

If analytics are processed asynchronously, document the resulting consistency and failure semantics, including possible loss or duplication and how those risks are handled.

### NFR-02: Database connection management

- Use connection pooling so that each request does not require establishing a new database connection.
- Manage connection and session lifecycles appropriately.

### NFR-03: Efficient statistics retrieval

- Avoid expensive or unnecessarily multi-stage queries when retrieving visit statistics.
- Explain how the chosen data model supports efficient statistics queries.

### NFR-04: Redirect latency and analytics overhead

- Analytics collection must not significantly increase redirect latency.
- Explain the selected analytics approach and its latency, reliability, and consistency trade-offs.

The brief does not define a numerical latency threshold.

### NFR-05: High-traffic performance

- Treat the redirect endpoint as the likely highest-traffic endpoint.
- Describe practical measures for handling several thousand requests per second without substantial performance degradation or service failure.
- Explain how the service would handle a sudden traffic increase caused by an advertising campaign.

The brief requests architectural reasoning for this traffic level. It does not explicitly require a measured throughput benchmark, a particular infrastructure stack, or deployment of every proposed scaling component.

### NFR-06: Multi-instance scalability

Provide `SCALABILITY.md` explaining:

- What must change when the service is deployed as multiple instances across multiple servers.
- Which dependencies or state must be separated from application instances or externalized.
- Which risks must be managed in that deployment model.
- Which implemented or proposed measures would keep the service available during a high-traffic campaign.

### NFR-07: Code quality and maintainability

- Use readable, modular Python code with a clear project structure.
- Demonstrate appropriate use of FastAPI and SQLAlchemy or SQLModel.
- Keep logging reusable.
- Make architectural decisions and trade-offs understandable to a reviewer.

## 3. Required documentation and deliverables

| Deliverable | Requirement |
| --- | --- |
| Complete project source code | Required |
| Alembic migrations | Required |
| `requirements.txt` | Required |
| `SCALABILITY.md` | Required |
| Supporting documentation | Required; explain design decisions, concurrency handling, and analytics alternatives |
| A small set of tests | Optional in the original brief |

Documentation must cover:

- URL lifecycle and repeated-submission policy, with trade-offs.
- Short-code uniqueness and collision handling.
- Concurrent inserts, concurrent visits, transaction handling, and count correctness.
- Analytics collection and alternative approaches.
- Redirect performance and efficient statistics retrieval.
- Multi-instance operation and campaign traffic handling.

## 4. Decisions left to the candidate

The following choices are not fixed by the assignment:

- Database engine and SQLAlchemy versus SQLModel.
- Request/response schemas and exact HTTP status codes.
- Accepted URL schemes and URL-equivalence or normalization rules.
- Short-code format, generation algorithm, and collision-retry policy.
- Same-URL/same-code versus same-URL/different-code behavior.
- Visit-count representation and analytics storage or delivery mechanism.
- Analytics consistency, visibility delay, and failure handling.
- Caching, queues, workers, and other scaling infrastructure, if justified.

These choices should be explicit and consistent with the required behavior. Proposed future architecture should be distinguished from functionality implemented in the submission.

## 5. Evaluation criteria

- Python code quality: structure, readability, and modularity.
- Correct use of FastAPI and SQLAlchemy or SQLModel.
- Database design.
- Clean, reusable logging.
- Quality of analysis in `SCALABILITY.md`.
- Practical, well-reasoned documentation.
- Attention to performance and scalability.

## 6. Information absent from the brief

The supplied PDF does not specify the submission deadline, submission channel, or policy on AI/tool assistance. Its 6–8-hour estimate is an effort estimate, not a submission deadline.
