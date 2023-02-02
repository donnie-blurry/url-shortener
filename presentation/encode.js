import validator from 'validator';
import shortener from '../application/encode.js';

export default (req, res) => {
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
  const shortUrl = shortener(protocolIncludedUrl);
  return res
    .status(200)
    .json({
      message: 'Success',
      data: shortUrl,
    });
};
