const validator = require('validator');

const encodeApp = require('../application/encode.js');

const presentation = {
  encode(req, res) {
    try {
      if (!req.body || !req.body.url) {
        return res
          .status(400)
          .json({
            message: 'Should provide a url to encode'
          });
      }
      const {url} = req.body;
      if (!validator.isURL(url)) {
        return res
          .status(400)
          .json({
            message: 'Should provide a valid url to encode'
          });
      }
      const shortUrl = encodeApp.encode(url);
      return res
        .status(200)
        .json({
          message: 'Success',
          data: shortUrl,
        });
    } catch (error) {
      if (error.code) {
        return res
          .status(error.code)
          .json({
            message: error.message
          });
      }
      return res
        .status(500)
        .json({
          message: 'Sorry, something on our went wrong.'
        });
    }
  }
};
module.exports = presentation;
