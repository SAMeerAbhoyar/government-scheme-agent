import React, { useEffect, useState } from 'react';
import api from '../services/api';
import { History as HistoryIcon, Search, Sparkles } from 'lucide-react';

export default function History() {
  const [searchHistory, setSearchHistory] = useState([]);
  const [recHistory, setRecHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const [searchRes, recRes] = await Promise.all([
        api.get('/history/search').catch(() => ({ data: [] })),
        api.get('/history/recommendations').catch(() => ({ data: [] }))
      ]);
      setSearchHistory(searchRes.data);
      setRecHistory(recRes.data);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="max-w-7xl mx-auto px-4 py-12 text-center text-gray-500">Loading activity history...</div>;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-200">
          <HistoryIcon className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Activity History</h1>
          <p className="text-xs text-gray-500">Audit trail of your past search queries and scheme recommendation evaluations</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Past Search Queries */}
        <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm space-y-4">
          <div className="flex items-center space-x-2 text-indigo-700 font-bold border-b border-gray-100 pb-3">
            <Search className="w-4 h-4" />
            <h3>Past Search Queries ({searchHistory.length})</h3>
          </div>
          {searchHistory.length === 0 ? (
            <p className="text-xs text-gray-400 py-4 text-center">No search query history logged yet.</p>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
              {searchHistory.map((item) => (
                <div key={item.id} className="p-3 bg-gray-50 rounded-xl border border-gray-100 text-xs flex justify-between items-start">
                  <div>
                    <p className="font-semibold text-gray-800">"{item.query || 'Category Search'}"</p>
                    {item.category && <span className="text-[10px] bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-medium mt-1 inline-block">{item.category}</span>}
                  </div>
                  <span className="text-[10px] text-gray-400 whitespace-nowrap">{new Date(item.created_at).toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Past Recommendation Runs */}
        <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm space-y-4">
          <div className="flex items-center space-x-2 text-purple-700 font-bold border-b border-gray-100 pb-3">
            <Sparkles className="w-4 h-4" />
            <h3>Evaluation History ({recHistory.length})</h3>
          </div>
          {recHistory.length === 0 ? (
            <p className="text-xs text-gray-400 py-4 text-center">No scheme recommendation runs logged yet.</p>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
              {recHistory.map((item) => (
                <div key={item.id} className="p-3 bg-gray-50 rounded-xl border border-gray-100 text-xs flex justify-between items-start">
                  <div>
                    <p className="font-semibold text-gray-800">{item.scheme_name}</p>
                    <span className={`text-[10px] px-2 py-0.5 rounded font-bold mt-1 inline-block ${
                      item.match_status === 'potentially_relevant' ? 'bg-emerald-100 text-emerald-800' :
                      item.match_status === 'cannot_determine' ? 'bg-amber-100 text-amber-800' : 'bg-gray-200 text-gray-700'
                    }`}>
                      {item.match_status}
                    </span>
                  </div>
                  <span className="text-[10px] text-gray-400 whitespace-nowrap">{new Date(item.created_at).toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
