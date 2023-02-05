import {Request, Response} from 'express';

import decodePresentation from '../decode';
import decodeApp from '../../application/decode';

describe('Decode presentation unit tests', () => {
  let mockResponse: Partial<Response>;
  let mockRequest : Partial<Request>;
  beforeEach(() => {
    mockResponse = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn(),
    };
  });

  it('should respond with an stored url if encoded url is valid and existing', () => {
    mockRequest = {query: {encodedUrl: 'short.link/ABCDEF'}};
    const storedUrl = {
      id: 'ABCDEF',
      shortUrl: 'short.link/ABCDEF',
      createdAt: Date.now(),
      originalUrl: 'https://example.com'
    };
    decodeApp.decode = jest.fn().mockReturnValueOnce(storedUrl);
    decodePresentation.decode(mockRequest as Request, mockResponse as Response);
    expect(decodeApp.decode).toBeCalledWith(mockRequest.query?.encodedUrl);
    expect(mockResponse.status).toBeCalledWith(200);
    expect(mockResponse.json).toBeCalledWith({
      data: storedUrl,
      message: 'Success',
    });
  });

  it('should respond with an error in no url is provided', () => {
    mockRequest = {query: {encodedUrl: ''}} ;
    decodePresentation.decode(mockRequest as Request, mockResponse as Response);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a url to decode',
    });
  });

  it('should respond with an error if encoded url is invalid', () => {
    mockRequest = {query: {encodedUrl: 'example'}};
    decodePresentation.decode(mockRequest as Request, mockResponse as Response);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a valid url',
    });
    mockRequest = {query: {encodedUrl: 'example.com>?'}};
    decodePresentation.decode(mockRequest as Request, mockResponse as Response);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a valid url',
    });
    mockRequest = {query: {encodedUrl: 'short.link.com'}};
    decodePresentation.decode(mockRequest as Request, mockResponse as Response);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a valid url',
    });
  });

  it('should respond with an error if url does not exist', () => {
    mockRequest = {query: {encodedUrl: 'short.link/ABCDEF'}};
    decodePresentation.decode(mockRequest as Request, mockResponse as Response);
    expect(mockResponse.status).toBeCalledWith(404);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Short url not found.',
    });
  });
});