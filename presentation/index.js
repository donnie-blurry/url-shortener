const express = require('express');
const helmet = require('helmet');

const rateLimiter = require('../middleware/rateLimiter');

const decodePresentation = require('./decode');
const encodePresentation = require('./encode');

const app = express();

app.use(helmet());
app.use(express.json());
app.use(rateLimiter);

app.use('/decode', decodePresentation.decode);
app.use('/encode', encodePresentation.encode);

module.exports = app;
