const db = require('./datastore');

const dataAccess = {
  getById(id) {
    return db.get(id);
  },
  store(urlObject) {
    db.set(urlObject.id, urlObject);
    return urlObject;
  },
};

module.exports = dataAccess;
