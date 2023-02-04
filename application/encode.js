const randomstring = require('randomstring');
const idGenerationConfig = require('../config/idGenerationConfig.js');
const dataAccess = require('../data-access/index.js');

const application = {
  encode (url) {
    let protocolIncludedUrl = url;
    if (!/^https?:\/\//i.test(url)) {
      protocolIncludedUrl = 'http://' + url;
    }
    let id;
    let tryCount = 0;
    do {
      id = randomstring.generate(idGenerationConfig);
      tryCount++;
      if (tryCount > idGenerationConfig.maxTryCount) {
        const error = new Error(`Could not generate a short url after ${tryCount} tries`);
        error.code = 500;
        throw error;
      }
    } while (dataAccess.getById(id));

    const shortenedUrlObject = {
      id,
      shortUrl: `http://short.link/${id}`,
      originalUrl: protocolIncludedUrl,
      createdAt: Date.now()
    };
    return dataAccess.store(shortenedUrlObject);
  },
};

module.exports = application;
