import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Dashboard from './components/Dashboard';
import DocumentList from './components/DocumentList';
import ReviewQueue from './pages/ReviewQueue';
import ReviewDetail from './pages/ReviewDetail';
import QA from './pages/QA';
import Settings from './pages/Settings';
import NotificationToast from './components/NotificationToast';
import ErrorBoundary from './components/ErrorBoundary';
import { fetchDocuments, fetchReviews } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [documents, setDocuments] = useState([]);
  const [pendingQueueCount, setPendingQueueCount] = useState(0);
  const [selectedReviewDocId, setSelectedReviewDocId] = useState(null);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    loadData();
    // Real-time automatic background polling (every 3 seconds)
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const docs = await fetchDocuments();
      setDocuments(docs);
      const queue = await fetchReviews('NEEDS_REVIEW', 1, 100);
      setPendingQueueCount(queue.total || 0);
    } catch (err) {
      console.error('Failed to load application data:', err);
    }
  };

  const showToast = (toastObj) => {
    setToast(toastObj);
  };

  const handleNavigate = (tab, docId = null) => {
    if (docId) {
      setSelectedReviewDocId(docId);
    }
    setActiveTab(tab);
  };

  const handleSelectDocumentForReview = (docId) => {
    setSelectedReviewDocId(docId);
    setActiveTab('review_detail');
  };

  const handleBackToQueue = () => {
    setSelectedReviewDocId(null);
    setActiveTab('review_queue');
    loadData();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Header
        activeTab={activeTab === 'review_detail' ? 'review_queue' : activeTab}
        setActiveTab={setActiveTab}
        reviewQueueCount={pendingQueueCount}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        <ErrorBoundary onRetry={loadData}>
          {/* Main User-Friendly Dashboard Tab */}
          {activeTab === 'dashboard' && (
            <Dashboard
              onNavigate={handleNavigate}
              onShowToast={showToast}
              onRefreshData={loadData}
            />
          )}

          {/* Documents Library Page Tab */}
          {activeTab === 'documents' && (
            <DocumentList
              documents={documents}
              onSelectDocument={handleSelectDocumentForReview}
              onRefresh={loadData}
              onShowToast={showToast}
            />
          )}

          {/* Ask Documents (RAG Chat Engine) */}
          {activeTab === 'qa' && (
            <QA onSelectDocument={handleSelectDocumentForReview} />
          )}

          {/* Human Review Queue List */}
          {activeTab === 'review_queue' && (
            <ReviewQueue onSelectDocument={handleSelectDocumentForReview} />
          )}

          {/* Human Review & Document Detail View */}
          {activeTab === 'review_detail' && (
            <ReviewDetail
              documentId={selectedReviewDocId}
              onBack={handleBackToQueue}
            />
          )}


        </ErrorBoundary>
      </main>

      <NotificationToast toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}
