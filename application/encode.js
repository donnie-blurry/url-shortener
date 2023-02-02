import randomstring from 'randomstring';
import { getById, store } from '../data-access/index.js';

export default function shorten (url) {
  let id;
  do {
    id = randomstring.generate({
      length: 6,
      readable: true,
      capitalization: 'uppercase'
    });
  } while (getById(id));

  const shortenedUrlObject = {
    id,
    shortUrl: `http://short.link/${id}`,
    originalUrl: url,
    createdAt: Date.now()
  };
  return store(shortenedUrlObject);
}
