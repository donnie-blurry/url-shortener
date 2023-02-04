const express = require('express');
const helmet = require('helmet');

const rateLimiter = require('../middleware/rateLimiter.js');

const decodePresentation = require('./decode.js');
const encodePresentation = require('./encode.js');

const app = express();

app.use(helmet());
app.use(express.json());
app.use(rateLimiter);

app.use('/decode', decodePresentation.decode);
app.use('/encode', encodePresentation.encode);

module.exports = app;
