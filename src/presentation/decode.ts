import {Request, Response} from 'express';
import validator from 'validator';

import decodeApp from '../application/decode';
import CustomError from '../types/Error';

const presentation = {
  decode(req: Request, res:Response) {
    try {
      const encodedUrl = req.query.encodedUrl as string;
      if (!encodedUrl) {
        return res
          .status(400)
          .json({
            message: 'Should provide a url to decode'
          });
      }
      if (!validator.isURL(encodedUrl)) {
        return res
          .status(400)
          .json({
            message: 'Should provide a valid url'
          });
      }
      const storedUrl = decodeApp.decode(encodedUrl);
      if (!storedUrl) {
        return res
          .status(404)
          .json({
            message: 'Short url not found.'
          });
      }
      return res
        .status(200)
        .json({
          message: 'Success',
          data: storedUrl
        });
    } catch (error) {
      if (error instanceof CustomError)
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
};

export default presentation;
