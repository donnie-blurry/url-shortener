import validator from 'validator';
import retriever from '../application/decode.js';

export default (req, res) => {
  const { encodedUrl } = req.query;
  if (!encodedUrl) {
    return res
      .status(400) // TODO what is the true status code?
      .json({
        message: 'Should provide a url to decode'
      });
  }
  if (!validator.isURL(encodedUrl)) {
    return res
      .status(400) // TODO what is the true status code?
      .json({
        message: 'Should provide a valid url'
      });
  }
  let protocolIncludedEncodedUrl = encodedUrl;
  if (!/^https?:\/\//i.test(encodedUrl)) {
    protocolIncludedEncodedUrl = 'http://' + encodedUrl;
  }
  const url = new URL(protocolIncludedEncodedUrl);
  if (url.host !== 'short.link') {
    return res
      .status(400) // TODO what is the true status code?
      .json({
        message: 'Should provide an short.link URL.'
      });
  }
  const shortUrlId = url.pathname.replace(/^\/+/g, '');
  const storedUrl = retriever(shortUrlId);
  if (!storedUrl) {
    return res
      .status(404)
      .json({
        message: 'Provided short.link URL does not exist.'
      });
  }
  return res
    .status(200)
    .json(storedUrl);
};
