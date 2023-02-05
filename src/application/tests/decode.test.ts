import decodeApp from '../decode';
import dataAccess from '../../data-access';
import {jest} from '@jest/globals';
describe('Decode application unit tests', () => {
  it('should respond with an error if encoded url is not short.link', async () => {
    const encodedUrl = 'example.com';
    expect(() => decodeApp.decode(encodedUrl)).toThrow('Should provide a short.link URL.');
  });
  
  it('should parse url and get pathname as short url id', () => {
    const url = 'https://www.short.link/ABCDEF';
    jest.spyOn(dataAccess, 'getById');
    decodeApp.decode(url);
    expect(dataAccess.getById).toBeCalledWith('ABCDEF');
  });
});