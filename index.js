const port = process.env.PORT || 5000;

import {app} from "./presentation/index.js";

app.listen(port, () =>
    console.log(`Example app listening on port ${port}!`),
);