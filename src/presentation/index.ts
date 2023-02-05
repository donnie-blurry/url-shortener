import express from 'express';
import helmet from 'helmet';
import rateLimiter from '../middleware/rateLimiter';
import decodePresentation from './decode';
import encodePresentation from './encode';

const app = express();

app.use(helmet());
app.use(express.json());
app.use(rateLimiter);

app.use('/decode', decodePresentation.decode);
app.use('/encode', encodePresentation.encode);

export default app;
