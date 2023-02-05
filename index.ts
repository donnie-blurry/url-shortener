import app from './src/presentation/index';
import port from './src/config/server';

app.listen(port, () =>
  console.log(`Url shortener running on port: ${port}`)
);
