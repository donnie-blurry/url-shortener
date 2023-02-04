const app = require('./presentation/index.js');

const port = require('./config/server.js');

app.listen(port, () =>
  console.log(`Url shortener running on port: ${port}`)
);
