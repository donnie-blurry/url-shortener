import db from './datastore.js';

export function getById (id) {
  return db.get(id);
}

export function store (urlObject) {
  db.set(urlObject.id, urlObject);
  return urlObject;
}
