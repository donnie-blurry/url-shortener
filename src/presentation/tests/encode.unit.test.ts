import {Request, Response} from 'express';

import { Presentation } from '../Presentation';
import encodeApp from '../../application/encode';

describe('Encode presentation unit tests', () => {
  let mockResponse: Partial<Response>;
  let mockRequest : Partial<Request>;
  beforeEach(() => {
    mockResponse = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn(),
    };
  });

  it('should respond with a short url', () => {
    mockRequest = {body : {url: 'https://example.com'}};
    const storedUrl = {
      id: 'ABCDEF',
      shortUrl: 'short.link/ABCDEF',
      createdAt: Date.now(),
      originalUrl: 'https://example.com'
    };
    encodeApp.encode = jest.fn().mockReturnValueOnce(storedUrl);
    Presentation.encode(mockRequest as Request, mockResponse as Response);
    expect(encodeApp.encode).toBeCalledWith(mockRequest.body.url);
    expect(mockResponse.status).toBeCalledWith(200);
    expect(mockResponse.json).toBeCalledWith({
      data: storedUrl,
      message: 'Success',
    });
  });

  it('should respond with an error if no url is provided', () => {
    mockRequest = {};
    Presentation.encode(mockRequest as Request, mockResponse as Response);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a url to encode',
    });
    mockRequest.body = {};
    Presentation.encode(mockRequest as Request, mockResponse as Response);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a url to encode',
    });
    mockRequest.body.url = '';
    Presentation.encode(mockRequest as Request, mockResponse as Response);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a url to encode',
    });
  });

  it('should respond with an error if url is invalid', () => {
    mockRequest = {body : {url: 'example'}};
    Presentation.encode(mockRequest as Request, mockResponse as Response);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a valid url to encode',
    });

    mockRequest.body.url = 'example.com<?';
    Presentation.encode(mockRequest as Request, mockResponse as Response);
    expect(mockResponse.status).toBeCalledWith(400);
    expect(mockResponse.json).toBeCalledWith({
      data: undefined,
      message: 'Should provide a valid url to encode',
    });
  });
});