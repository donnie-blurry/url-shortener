const validator = require('validator');

const encodeApp = require('../application/encode.js');

const presentation = {
  encode(req, res) {
    const {url} = req.body;
    if (!url) {
      return res
        .status(400)
        .json({
          message: 'Should provide a url to encode'
        });
    }
    if (!validator.isURL(url)) {
      return res
        .status(400)
        .json({
          message: 'Should provide a valid url to encode'
        });
    }
    let protocolIncludedUrl = url;
    if (!/^https?:\/\//i.test(url)) {
      protocolIncludedUrl = 'http://' + url;
    }
    const shortUrl = encodeApp.encode(protocolIncludedUrl);
    return res
      .status(200)
      .json({
        message: 'Success',
        data: shortUrl,
      });
  }
};
module.exports = presentation;
