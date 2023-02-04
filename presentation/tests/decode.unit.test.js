const decodePresentation = require('../decode.js');
const decodeApp = require('../../application/decode');

describe('Decode presentation unit tests', () => {
  let mockResponse;
  beforeEach(() => {
    mockResponse = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn(),
    };
  });

  it('should respond with an stored url if encoded url is valid and existing', () => {
    const request = {
      query: {
        encodedUrl: 'short.link/ABCDEF'
      }
    };
    const storedUrl = {
      id: 'ABCDEF',
      shortUrl: 'short.link/ABCDEF',
      createdAt: Date.now(),
      originalUrl: 'https://example.com'
    };
    decodeApp.decode = jest.fn().mockReturnValueOnce(storedUrl);
    decodePresentation.decode(request, mockResponse);
    expect(decodeApp.decode).toBeCalledWith(request.query.encodedUrl)
    expect(mockResponse.status).toBeCalledWith(200);
    expect(mockResponse.json).toBeCalledWith({
      data: storedUrl,
      message: 'Success',
    });
  });

  it('should respond with an error in no url is provided', () => {
    const request = {query: {}};
    decodePresentation.decode(request, mockResponse);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a url to decode',
    });
  });

  it('should respond with an error if encoded url is invalid', () => {
    const request = {query: {encodedUrl: 'example'}};
    decodePresentation.decode(request, mockResponse);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a valid url',
    });
    request.query.encodedUrl = 'example.com>?';
    decodePresentation.decode(request, mockResponse);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a valid url',
    });
    request.query.encodedUrl = 'short.link.com';
    decodePresentation.decode(request, mockResponse);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a valid url',
    });
  });

  it('should respond with an error if url does not exist', () => {
    const request = {
      query: {
        encodedUrl: 'short.link/ABCDEF'
      }
    };
    decodePresentation.decode(request, mockResponse);
    expect(mockResponse.status).toBeCalledWith(404);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Short url not found.',
    });
  });
});