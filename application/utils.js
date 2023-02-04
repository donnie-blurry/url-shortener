const utils = {
  getCompleteUrl(encodedUrl) {
    let protocolIncludedEncodedUrl = encodedUrl;
    if (!/^https?:\/\//i.test(encodedUrl)) {
      protocolIncludedEncodedUrl = 'http://' + encodedUrl;
    }
    return protocolIncludedEncodedUrl;
  }
};

module.exports = utils;

