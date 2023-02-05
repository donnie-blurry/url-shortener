/** @type {import('jest').Config} */
const config = {
  verbose: true,
  preset: 'ts-jest',
  testEnvironment: 'node',
  modulePathIgnorePatterns: ['<rootDir>/dist/']

};

module.exports = config;