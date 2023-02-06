import {Request, Response, Router} from 'express';

export const router: Router = Router();

import validator from 'validator';

import encodeApp from '../application/encode';
import decodeApp from '../application/decode';

import CustomError from '../types/Error';
import {ShortUrl} from '../types/ShortUrl';

export class Presentation {
  private static setResponseStatusAndJson(res: Response, code: number, message: string, data?: any) {
    res
      .status(code)
      .json({
        message,
        data,
      });
  }

  static encode(req: Request, res: Response) {
    try {
      if (!req.body || !req.body.url) {
        return Presentation.setResponseStatusAndJson(res, 400, 'Should provide a url to encode');
      }
      const url = req.body.url as string;
      if (!validator.isURL(url)) {
        return Presentation.setResponseStatusAndJson(res, 400, 'Should provide a valid url to encode');
      }
      const shortUrl: ShortUrl = encodeApp.encode(url);
      return Presentation.setResponseStatusAndJson(res, 200, 'Success', shortUrl);
    } catch (error) {
      if (error instanceof CustomError) {
        return Presentation.setResponseStatusAndJson(res, error.code, error.message);
      }
      return Presentation.setResponseStatusAndJson(res, 500, 'Sorry, something on our end went wrong.');

    }
  }

  static decode(req: Request, res: Response) {
    try {
      const encodedUrl = req.query.encodedUrl as string;
      if (!encodedUrl) {
        return Presentation.setResponseStatusAndJson(res, 400, 'Should provide a url to decode');
      }
      if (!validator.isURL(encodedUrl)) {
        return Presentation.setResponseStatusAndJson(res, 400, 'Should provide a valid url to encode');
      }
      const storedUrl = decodeApp.decode(encodedUrl);
      if (!storedUrl) {
        return Presentation.setResponseStatusAndJson(res, 404, 'Encoded url not found!');
      }
      return Presentation.setResponseStatusAndJson(res, 200, 'Success', storedUrl);
    } catch (error) {
      if (error instanceof CustomError)
        return Presentation.setResponseStatusAndJson(res, error.code, error.message);
    }
    return Presentation.setResponseStatusAndJson(res, 500, 'Sorry, something on our end went wrong.');
  }
}


router.post('/encode', Presentation.encode);
router.get('/decode', Presentation.decode);
