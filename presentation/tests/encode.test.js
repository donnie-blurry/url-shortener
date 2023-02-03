import db from '../../data-access/datastore.js';
import {app} from '../index.js';

import request from 'supertest';

describe('/encode route', () => {
  beforeEach(() => {
    db.flushAll();
  });

  it('should respond with a successfully created short url', async () => {
    const sampleUrl = 'https://www.example.com/example';
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
  });

  it('should respond with an error if url is faulty', async () => {
    const sampleUrl = 'example';
    const response = await request(app)
      .post('/encode')
      .send({url: sampleUrl})
      .set('Accept', 'application/json')
      .expect('Content-Type', /json/);
    expect(response.statusCode).toEqual(400);
    expect(response.body.message).toEqual('Should provide a valid url to encode');
    expect(response.body.data).toBeUndefined();
  });

  it('should respond with an error if no url is provided', async () => {
    const sampleUrl = '';
    const response = await request(app)
      .post('/encode')
      .send({url: sampleUrl})
      .set('Accept', 'application/json')
      .expect('Content-Type', /json/);
    expect(response.statusCode).toEqual(400);
    expect(response.body.message).toEqual('Should provide a url to encode');
    expect(response.body.data).toBeUndefined();
  });
});