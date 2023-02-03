import express from 'express';
import decoder from './decode.js';
import encoder from './encode.js';

export const app = express();

app.use(express.json());

app.use('/decode', decoder);
app.use('/encode', encoder);
