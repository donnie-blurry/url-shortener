import {getById} from "../data-access/index.js";

export default function getUrlById(shortUrlId) {
    return getById(shortUrlId);
}
