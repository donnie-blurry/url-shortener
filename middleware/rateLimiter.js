const rateLimit = require('express-rate-limit');

const rateLimitConfig = require('../config/rateLimit.js');

const limiter = rateLimit(rateLimitConfig);

module.exports = limiter;
