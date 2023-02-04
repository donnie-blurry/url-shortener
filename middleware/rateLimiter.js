const rateLimit = require('express-rate-limit');

const rateLimitConfig = require('../config/rateLimit');

const limiter = rateLimit(rateLimitConfig);

module.exports = limiter;
