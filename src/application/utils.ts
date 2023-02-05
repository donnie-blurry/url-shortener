const utils = {
  getCompleteUrl(encodedUrl: string) {
    let protocolIncludedEncodedUrl = encodedUrl;
    if (!/^https?:\/\//i.test(encodedUrl)) {
      protocolIncludedEncodedUrl = 'http://' + encodedUrl;
    }
    return protocolIncludedEncodedUrl;
  }
};

export default utils;

