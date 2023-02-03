import validator from 'validator';
import decoder from '../application/decode.js';

export default (req, res) => {
  try {
    const {encodedUrl} = req.query;
    if (!encodedUrl) {
      return res
        .status(400)
        .json({
          message: 'Should provide a url to decode'
        });
    }
    if (!validator.isURL(encodedUrl)) {
      return res
        .status(400)
        .json({
          message: 'Should provide a valid url'
        });
    }
    const storedUrl = decoder(encodedUrl);
    if (!storedUrl) {
      return res
        .status(404)
        .json({
          message: 'Short url not found.'
        });
    }
    return res
      .status(200)
      .json({
        message: 'Success',
        data: storedUrl
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
};
