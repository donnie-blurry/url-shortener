import app from './presentation/index.js';

import {port} from './config/server.js';

app.listen(port, () =>
  console.log(`Url shortener running on port: ${port}`)
);
