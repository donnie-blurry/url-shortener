const PORT = 5000;
import express from 'express';
import validator from 'validator';

const app = express();

function getUrlById(shortUrlId) {
    return {
        id: shortUrlId,
        shortUrl: `http://short.link/${shortUrlId}`,
        originalUrl: "https://example.com",
        createdAt: Date.now(),
    };
}

app.get('/decode', (req, res) => {
    const {encodedUrl} = req.query;
    if (!encodedUrl) {
        return res
            .status(400) // TODO what is the true status code?
            .json({
                message: "Should provide an encodedUrl"
            });
    }
    if (!validator.isURL(encodedUrl)) {
        return res
            .status(400) // TODO what is the true status code?
            .json({
                message: "Should provide an valid encodedUrl"
            });
    }
    let protocolIncludedEncodedUrl = encodedUrl;
    if (!/^https?:\/\//i.test(encodedUrl)) {
        protocolIncludedEncodedUrl = 'http://' + encodedUrl;
    }
    const url = new URL(protocolIncludedEncodedUrl);
    if (url.host !== 'short.link') {
        return res
            .status(400) // TODO what is the true status code?
            .json({
                message: "Should provide an short.link URL."
            });
    }
    const shortUrlId = url.pathname.replace(/^\/+/g, '');
    const storedUrl = getUrlById(shortUrlId);
    if (!storedUrl) {
        return res
            .status(404)
            .json({
                message: "Provided short.link URL does not exist."
            });
    }
    return res
        .status(200)
        .json(storedUrl);
}).listen(PORT, () =>
    console.log(`Example app listening on port ${PORT}!`),
);