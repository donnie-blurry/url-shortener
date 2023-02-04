const db = require('./datastore.js');

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
