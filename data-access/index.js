const urlObjects = []

export function getById(id) {
    return urlObjects.find(element => element.id === id);
}

export function store(urlObject) {
    urlObjects.push(urlObject);
    return urlObject;
}
