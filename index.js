import { app } from './presentation/index.js';

const port = process.env.PORT || 5000;

app.listen(port, () =>
  console.log(`Example app listening on port ${port}!`)
);
