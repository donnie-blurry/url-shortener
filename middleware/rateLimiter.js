import rateLimit from 'express-rate-limit';

import rateLimitConfig from '../config/rateLimit.js';

const limiter = rateLimit(rateLimitConfig);

export default limiter;
