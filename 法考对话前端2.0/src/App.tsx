/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Layout } from './components/Layout';
import { ErrorBoundary } from './components/ErrorBoundary';
import { MindmapPreviewPage } from './components/MindmapPreviewPage';

export default function App() {
  const pathname = typeof window !== 'undefined' ? window.location.pathname : '/';
  const isMindmapPreviewRoute = pathname === '/mindmap-preview';

  return (
    <ErrorBoundary>
      {isMindmapPreviewRoute ? <MindmapPreviewPage /> : <Layout />}
    </ErrorBoundary>
  );
}
