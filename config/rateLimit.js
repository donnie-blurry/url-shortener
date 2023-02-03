const rateLimitConfig = {
  windowMs: 60 * 60 * 1000, // 1 hour
  max: 50, // Limit each IP to 5 create account requests per `window` (here, per hour)
  standardHeaders: true, // Return rate limit info in the `RateLimit-*` headers
  legacyHeaders: false, // Disable the `X-RateLimit-*` headers
};

export default rateLimitConfig;