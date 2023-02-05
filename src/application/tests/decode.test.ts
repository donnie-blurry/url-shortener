import decodeApp from '../decode';

describe('Decode application unit tests', () => {
  it('should respond with an error if encoded url is not short.link', async () => {
    const encodedUrl = 'example.com';
    expect(() => decodeApp.decode(encodedUrl)).toThrow('Should provide a short.link URL.');
  });
});