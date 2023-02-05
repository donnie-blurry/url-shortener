import dataAccess from '../data-access';
import utils from './utils';
import CustomError from '../types/Error';
import {ShortUrl} from '../types/ShortUrl';

function getShortUrlId(protocolIncludedEncodedUrl: string) : string {
  const url = new URL(protocolIncludedEncodedUrl);
  if (url.host !== 'short.link' && url.host !== 'www.short.link') {
    throw new CustomError('Should provide a short.link URL.', 400);
  }
  return url.pathname.replace(/^\/+/g, '');
}

const application = {
  decode(encodedUrl: string) : ShortUrl{
    const completeUrl = utils.getCompleteUrl(encodedUrl);
    const shortUrlId = getShortUrlId(completeUrl);
    return dataAccess.getById(shortUrlId);
  }
};

export default application;
