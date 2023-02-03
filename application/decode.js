import { getById } from '../data-access/index.js';

export default function decoder (encodedUrl) {
  let protocolIncludedEncodedUrl = encodedUrl;
  if (!/^https?:\/\//i.test(encodedUrl)) {
    protocolIncludedEncodedUrl = 'http://' + encodedUrl;
  }
  const url = new URL(protocolIncludedEncodedUrl);
  if (url.host !== 'short.link' && url.host !== 'www.short.link') {
    const error = new Error('Should provide a short.link URL.');
    error.code = 400;
    throw error;
  }
  const shortUrlId = url.pathname.replace(/^\/+/g, '');
  return getById(shortUrlId);
}
