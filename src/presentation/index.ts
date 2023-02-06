import express from 'express';
import helmet from 'helmet';
import rateLimiter from '../middleware/rateLimiter';
import {router} from './Presentation';

const app = express();

app.use(helmet());
app.use(express.json());
app.use(rateLimiter);

app.use('/', router);

export default app;
