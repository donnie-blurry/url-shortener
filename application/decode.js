const dataAccess = require('../data-access/index');

const utils = require('./utils');

function getShortUrlId(protocolIncludedEncodedUrl) {
  const url = new URL(protocolIncludedEncodedUrl);
  if (url.host !== 'short.link' && url.host !== 'www.short.link') {
    const error = new Error('Should provide a short.link URL.');
    error.code = 400;
    throw error;
  }
  return url.pathname.replace(/^\/+/g, '');
}

const application = {
  decode(encodedUrl) {
    const completeUrl = utils.getCompleteUrl(encodedUrl);
    const shortUrlId = getShortUrlId(completeUrl);
    return dataAccess.getById(shortUrlId);
  }
};

module.exports = application;
