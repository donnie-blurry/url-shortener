import express from 'express';
import helmet from 'helmet';

import rateLimiter from '../middleware/rateLimiter.js';

import decoder from './decode.js';
import encoder from './encode.js';

const app = express();

app.use(helmet());
app.use(express.json());
app.use(rateLimiter);

app.use('/decode', decoder);
app.use('/encode', encoder);

export default app;
