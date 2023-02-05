import randomstring from 'randomstring';
import idGenerationConfig from '../config/idGenerationConfig';
import dataAccess from '../data-access';
import utils from './utils';
import CustomError from '../types/Error';
import {ShortUrl} from '../types/ShortUrl';
const application = {
  encode (url: string) : ShortUrl {
    const completeUrl = utils.getCompleteUrl(url);
    let id;
    let tryCount = 0;
    do {
      id = randomstring.generate(idGenerationConfig as Randomstring.GenerateOptions);
      tryCount++;
      if (tryCount > idGenerationConfig.maxTryCount) {
        throw new CustomError(`Could not generate a short url after ${tryCount} tries`, 500);
      }
    } while (dataAccess.getById(id));

    const shortenedUrlObject: ShortUrl = {
      id,
      shortUrl: `http://short.link/${id}`,
      originalUrl: completeUrl,
      createdAt: Date.now()
    };
    return dataAccess.store(shortenedUrlObject);
  },
};

export default application;
