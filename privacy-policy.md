# Privacy Policy for Semantic Scholar Research API

Last updated: 2026-03-10

This API provides a wrapper around the Semantic Scholar API for academic research workflows, including paper search, paper detail retrieval, related paper retrieval, reading-list generation, and foundational paper discovery.

## Data Collection

This API does not intentionally collect, sell, or share personal user data.

Requests to this API may be logged by the hosting provider and application server for operational, debugging, rate-limiting, and security purposes. Logged data may include:

- IP address
- request timestamps
- requested endpoints
- query parameters
- response status codes

These logs are used only to operate and secure the service.

## Upstream Data Source

This API retrieves scholarly metadata from Semantic Scholar and may transmit user queries to the Semantic Scholar service in order to fulfill requests.

Upstream source:
- https://www.semanticscholar.org/product/api

This API does not claim ownership of upstream metadata.

## Credentials and Secrets

If an upstream API key is used, it is stored server-side as an environment variable and is not exposed to end users.

## Data Retention

This service may use short-term caching to reduce repeated upstream requests and improve performance. Cached results are temporary and are not intended as a permanent data store.

Operational logs and cached data may be deleted periodically.

## Third-Party Services

This API may rely on third-party infrastructure providers, including:

- Render or similar hosting providers
- Semantic Scholar API

Those services may process request metadata according to their own policies.

## Personal Data

Do not submit sensitive personal data, confidential student records, private health information, financial information, or other restricted data through this API.

## Intended Use

This API is intended for academic research assistance, literature discovery, reading-list generation, and study support.

## Contact

For questions about this API or this privacy policy, contact the maintainer through the associated GitHub repository.