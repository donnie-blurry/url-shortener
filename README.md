# Url Shortener

A simple URL shortener built using Node.js, the Express framework and node-cache as in-memory storage. The service
provides two APIs for encoding and decoding a url, each respectively mean to shorten a url and get the original url from
the shortened version.

Author: Danial Sheikhani

### Framework

Express - A popular web app framework in node.js, had previous experience, so it was my go-to option

### File structure

There are 3 main layers that depend on each layer:

* **Presentation** knows about express and Rest APIs, gets values from APIs, depends on **Application's** work and then
  responds with JSON values on those APIs
* **Application** handles the business logics, creates a random string as a short url and then makes sure that it is not
  already taken, it tries up to a maximum number set in environment variable before giving up, it is not concerned about
  input validation, does not know about the details of database, but depends on **Data-Access** layer.
* **Data-Access** Node-cache is used as an in-memory DB, could be easily changed to an actual DB like MongoDB

This separation of layers helps that each layer to be modified or extended without much change to any other layer. It
also makes testing in isolation easier

### Security

Following security best practices for production in expressjs.com I used helmet middleware to set some secure headers
and also added a rate limiter to be safe against brute-force attacks

### Tests

Tests are powered by jest testing framework and supertest for mocking http requests

There are end-to-end tests for each route in presentation layer which only mocks the requests.

There are integration tests that test the interaction and relation between each piece of code with its dependencies,
These tests check how, with what arguments the dependencies were called.

There are also unit tests for each layer independently which tries to test only the main goal of that layer with mocking
its dependencies

## Getting Started

```bash
npm install
npm run build
npm start
```

To run tests:

```bash
npm install
npm run test
```

## How to Use the Project

### POST /encode

Request:

```bash
curl --request POST \
  --url http://localhost:3000/encode \
  --header 'Content-Type: application/json' \
  --data '{
	"url": "example.com"
}'
```

Response:

```bash
{
	"message": "Success",
	"data": {
		"id": "3GG45J",
		"shortUrl": "http://short.link/3GG45J",
		"originalUrl": "http://example.com",
		"createdAt": 1675521941565
	}
}
```

------------

### GET /decode

Request:

```bash
curl --request GET \
  --url 'http://localhost:3000/decode?encodedUrl=short.link%2F3GG45J'
```

Response:

```bash
{
	"message": "Success",
	"data": {
		"id": "3GG45J",
		"shortUrl": "http://short.link/3GG45J",
		"originalUrl": "http://example.com",
		"createdAt": 1675521941565
	}
}
```

## Video Demonstration
