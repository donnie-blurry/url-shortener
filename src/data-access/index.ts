import db from './datastore';
import {ShortUrl} from '../types/ShortUrl';

const dataAccess = {
  getById(id: string) : ShortUrl {
    return db.get(id) as ShortUrl;
  },
  store(urlObject: ShortUrl) : ShortUrl {
    db.set(urlObject.id, urlObject);
    return urlObject;
  },
};

export default dataAccess;
