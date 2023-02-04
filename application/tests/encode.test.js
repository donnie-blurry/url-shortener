const encodeApp = require('../encode.js');
const dataAccess = require('../../data-access/index.js');
const db = require('../../data-access/datastore.js');

describe('encode', () => {
  beforeEach(() => {
    db.flushAll();
  });

  it('should throw an error when there are too many collisions', async () => {
    // Creating collision by returning a stored url no matter what the id is.
    dataAccess.getById = jest.fn().mockReturnValue({
      createdAt: Date.now(),
      id: 'ABCDEF',
      shortUrl: 'https://short.link/ABCDEF',
      url: 'https://example.com/',
    });
    const sampleUrl = 'https://www.example.com/example';
    expect(() => encodeApp.encode(sampleUrl)).toThrow(/Could not generate a short url after/);
  });
});