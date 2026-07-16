import { Lamatic } from 'lamatic'

export const lamaticClient = new Lamatic({
    endpoint: process.env.LAMATIC_PROJECT_ENDPOINT || 'dummy-endpoint',
    projectId: process.env.LAMATIC_PROJECT_ID || 'dummy-id',
    apiKey: process.env.LAMATIC_PROJECT_API_KEY || 'dummy-key',
})
