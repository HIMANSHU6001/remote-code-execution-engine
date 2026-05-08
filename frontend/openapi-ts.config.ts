import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: '../openapi.json',
  output: 'src/lib/api-client',
  plugins: [
    '@hey-api/client-fetch',
    {
      name: '@hey-api/sdk',
      transformer: true,
    }
  ],
});
