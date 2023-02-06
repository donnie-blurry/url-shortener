import request from 'supertest';
import db from '../../data-access/datastore';
import app from '../index';

describe('/decode route end to end tests', () => {
  beforeEach(() => {
    db.flushAll();
  });

  it('should respond with original url for a valid short url', async () => {
    const mockObject = {
      id: 'ABCDEF',
      createdAt: Date.now(),
      originalUrl: 'https://www.example.com',
      shortUrl: 'http://short.link/ABCDEF',
    };
    db.set(mockObject.id, mockObject);
    const firstResponse = await request(app)
      .get(`/decode?encodedUrl=${mockObject.shortUrl}`)
      .set('Accept', 'application/json')
      .expect('Content-Type', /json/);
    expect(firstResponse.statusCode).toEqual(200);
    expect(firstResponse.body.message).toEqual('Success');
    expect(firstResponse.body.data.id).toEqual(mockObject.id);
    expect(firstResponse.body.data.shortUrl).toEqual(mockObject.shortUrl);
    expect(firstResponse.body.data.originalUrl).toEqual(mockObject.originalUrl);

    const secondResponse = await request(app)
      .get('/decode?encodedUrl=short.link/ABCDEF')
      .set('Accept', 'application/json')
      .expect('Content-Type', /json/);
    expect(secondResponse.statusCode).toEqual(200);
    expect(secondResponse.body.message).toEqual('Success');
    expect(secondResponse.body.data.id).toEqual(mockObject.id);
    expect(secondResponse.body.data.shortUrl).toEqual(mockObject.shortUrl);
    expect(secondResponse.body.data.originalUrl).toEqual(mockObject.originalUrl);

    const thirdResponse = await request(app)
      .get('/decode?encodedUrl=www.short.link/ABCDEF')
      .set('Accept', 'application/json')
      .expect('Content-Type', /json/);
    expect(thirdResponse.statusCode).toEqual(200);
    expect(thirdResponse.body.message).toEqual('Success');
    expect(thirdResponse.body.data.id).toEqual(mockObject.id);
    expect(thirdResponse.body.data.shortUrl).toEqual(mockObject.shortUrl);
    expect(thirdResponse.body.data.originalUrl).toEqual(mockObject.originalUrl);
  });

  it('should respond with an error if short url does not exist', async () => {
    const firstResponse = await request(app)
      .get('/decode?encodedUrl=www.short.link/ABCDEF')
      .set('Accept', 'application/json')
      .expect('Content-Type', /json/);
    expect(firstResponse.statusCode).toEqual(404);
    expect(firstResponse.body.message).toEqual('Encoded url not found!');

  });

  it('should respond with an error if no url is provided', async () => {
    const response = await request(app)
      .get('/decode')
      .set('Accept', 'application/json')
      .expect('Content-Type', /json/);
    expect(response.statusCode).toEqual(400);
    expect(response.body.message).toEqual('Should provide a url to decode');
    expect(response.body.data).toBeUndefined();
  });

  it('should respond with an error if url is not valid', async () => {
    const response = await request(app)
      .get('/decode?encodedUrl=example')
      .set('Accept', 'application/json')
      .expect('Content-Type', /json/);
    expect(response.statusCode).toEqual(400);
    expect(response.body.message).toEqual('Should provide a valid url to encode');
    expect(response.body.data).toBeUndefined();
  });

  it('should respond with an error if url is not our encoded url', async () => {
    const response = await request(app)
      .get('/decode?encodedUrl=example.com')
      .set('Accept', 'application/json')
      .expect('Content-Type', /json/);
    expect(response.statusCode).toEqual(400);
    expect(response.body.message).toEqual('Should provide a short.link URL.');
    expect(response.body.data).toBeUndefined();
  });
});