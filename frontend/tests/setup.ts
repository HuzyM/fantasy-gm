import '@testing-library/jest-dom/vitest';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(cleanup);

// The fixture UI has no reason to contact any service, even in component tests.
vi.stubGlobal('fetch', () => {
  throw new Error('Network access is not allowed in fixture tests');
});
