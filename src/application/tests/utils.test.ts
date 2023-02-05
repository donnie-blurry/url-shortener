import utils from '../utils';

describe('Utils unit tests', () => {
  it('should add http protocol if no protocol is in the url', async () => {
    const noProtocolUrl = 'example.com';
    expect(utils.getCompleteUrl(noProtocolUrl)).toBe('http://' + noProtocolUrl);
    const looksLikeHasProtocolUrl = 'http.example.com';
    expect(utils.getCompleteUrl(looksLikeHasProtocolUrl)).toBe('http://' + looksLikeHasProtocolUrl);
  });

  it('should return the same url if it has a protocol', async () => {
    const protocolIncludedUrl = 'http://example.com';
    expect(utils.getCompleteUrl(protocolIncludedUrl)).toBe(protocolIncludedUrl);
  });
});