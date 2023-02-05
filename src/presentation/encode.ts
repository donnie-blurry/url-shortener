import {Request, Response} from 'express';
import validator from 'validator';

import encodeApp from '../application/encode';
import CustomError from '../types/Error';

const presentation = {
  encode(req: Request, res:Response) {
    try {
      if (!req.body || !req.body.url) {
        return res
          .status(400)
          .json({
            message: 'Should provide a url to encode'
          });
      }
      const url = req.body.url as string;
      if (!validator.isURL(url)) {
        return res
          .status(400)
          .json({
            message: 'Should provide a valid url to encode'
          });
      }
      const shortUrl = encodeApp.encode(url);
      return res
        .status(200)
        .json({
          message: 'Success',
          data: shortUrl,
        });
    } catch (error) {
      if (error instanceof CustomError) {
        return res
          .status(error.code)
          .json({
            message: error.message
          });
      }
      return res
        .status(500)
        .json({
          message: 'Sorry, something on our went wrong.'
        });
    }
  }
};
export default presentation;