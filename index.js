const app = require('./presentation/index');

const port = require('./config/server');

app.listen(port, () =>
  console.log(`Url shortener running on port: ${port}`)
);
