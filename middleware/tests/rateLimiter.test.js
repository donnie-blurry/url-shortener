const request = require('supertest');

const rateLimitConfig = require('../../config/rateLimit');

const db = require('../../data-access/datastore');
const app = require('../../presentation/index');

describe('/encode rate limiter', () => {
  beforeEach(() => {
    db.flushAll();
  });

  it('should eventually respond with a too many request error ', async () => {
    const sampleUrl = 'https://www.example.com/example';
    for (let i = 0; i < rateLimitConfig.max; i++) {
      const response = await request(app)
        .post('/encode')
        .send({url: sampleUrl})
        .set('Accept', 'application/json')
        .expect('Content-Type', /json/);
      expect(response.statusCode).toEqual(200);
      expect(response.body.message).toEqual('Success');
      expect(response.body).toMatchObject({
        message: 'Success',
        data: {
          id: expect.any(String),
          shortUrl: expect.any(String),
          originalUrl: sampleUrl,
        },
      });
    }
    const response = await request(app)
      .post('/encode')
      .send({url: sampleUrl})
      .set('Accept', 'application/json');
    expect(response.statusCode).toEqual(429);
    expect(response.text).toEqual('Too many requests, please try again later.');
  });
});