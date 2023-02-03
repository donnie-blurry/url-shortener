import validator from "validator";

function shorten(url) {
    return {
        id: "QAZWSX",
        shortUrl: "http://short.link/QAZWSX",
        originalUrl: url,
        createdAt: Date.now(),
    };
}

export default (req, res) => {
    const {url} = req.body;
    if (!url) {
        return res
            .status(400)
            .json({
                message: "Should provide a url to encode"
            });
    }
    if (!validator.isURL(url)) {
        return res
            .status(400) // TODO what is the true status code?
            .json({
                message: "Should provide a valid url to encode"
            });
    }
    let protocolIncludedUrl = url;
    if (!/^https?:\/\//i.test(url)) {
        protocolIncludedUrl = 'http://' + url;
    }
    const shortUrl = shorten(protocolIncludedUrl);
    return res
        .status(200)
        .json(shortUrl);
}