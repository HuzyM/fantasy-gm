const configuredPort = process.env.BROWSER_TEST_PORT || '4173';
if (!/^\d+$/.test(configuredPort) || +configuredPort < 1024 || +configuredPort > 65535)
  throw new Error('BROWSER_TEST_PORT must be an integer from 1024 to 65535');

export const browserPort = +configuredPort;
export const browserOrigin = `http://127.0.0.1:${browserPort}`;
