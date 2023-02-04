const encodePresentation = require('../encode');
const encodeApp = require('../../application/encode');

describe('Encode presentation unit tests', () => {
  let mockResponse;
  beforeEach(() => {
    mockResponse = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn(),
    };
  });

  it('should respond with a short url', () => {
    const request = {body : {url: 'https://example.com'}};
    const storedUrl = {
      id: 'ABCDEF',
      shortUrl: 'short.link/ABCDEF',
      createdAt: Date.now(),
      originalUrl: 'https://example.com'
    };
    encodeApp.encode = jest.fn().mockReturnValueOnce(storedUrl);
    encodePresentation.encode(request, mockResponse);
    expect(encodeApp.encode).toBeCalledWith(request.body.url);
    expect(mockResponse.status).toBeCalledWith(200);
    expect(mockResponse.json).toBeCalledWith({
      data: storedUrl,
      message: 'Success',
    });
  });

  it('should respond with an error if no url is provided', () => {
    const request = {};
    encodePresentation.encode(request, mockResponse);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a url to encode',
    });
    request.body = {};
    encodePresentation.encode(request, mockResponse);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a url to encode',
    });
    request.body.url = '';
    encodePresentation.encode(request, mockResponse);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a url to encode',
    });
  });

  it('should respond with an error if url is invalid', () => {
    const request = {body : {url: 'example'}};
    encodePresentation.encode(request, mockResponse);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a valid url to encode',
    });

    request.body.url = 'example.com<?';
    encodePresentation.encode(request, mockResponse);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a valid url to encode',
    });
  });
});