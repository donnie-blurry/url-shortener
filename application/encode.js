import randomstring from "randomstring";

const urlObjects = []

function getUrlById(id) {
    return urlObjects.find(element => element.id === id);
}

function store(urlObject) {
    urlObjects.push(urlObject);
    return urlObject;
}

export default function shorten(url) {
    let id;
    do {
        id = randomstring.generate({
            length: 6,
            readable: true,
            capitalization: 'uppercase',
        })
    } while (getUrlById(id))

    let shortenedUrlObject = {
        id,
        shortUrl: `http://short.link/${id}`,
        originalUrl: url,
        createdAt: Date.now(),
    };
    return store(shortenedUrlObject);
}
