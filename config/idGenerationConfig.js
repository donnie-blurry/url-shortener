const idGenerationConfig = {
  length: process.env.SHORT_URL_LENGTH || 6,
  readable: process.env.READABLE_URLS || true,
  capitalization: process.env.SHORT_URL_CAPITALIZATION || 'uppercase',
};

export default idGenerationConfig;