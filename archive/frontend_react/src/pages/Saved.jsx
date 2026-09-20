import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { Bookmark, Trash2, ArrowRight } from 'lucide-react';

export default function Saved() {
  const [savedSchemes, setSavedSchemes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSaved();
  }, []);

  const loadSaved = async () => {
    try {
      const res = await api.get('/schemes/saved');
      setSavedSchemes(res.data);
    } catch (err) {
      console.error('Failed to load saved schemes:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUnsave = async (schemeId) => {
    try {
      await api.delete(`/schemes/${schemeId}/save`);
      setSavedSchemes(prev => prev.filter(s => s.scheme_id !== schemeId));
    } catch (err) {
      console.error('Failed to remove saved scheme:', err);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center text-gray-500">
        Loading saved schemes...
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center border border-amber-200">
          <Bookmark className="w-5 h-5 fill-current" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Saved Bookmarks</h1>
          <p className="text-xs text-gray-500">Quickly access government schemes you have bookmarked</p>
        </div>
      </div>

      {savedSchemes.length === 0 ? (
        <div className="bg-white rounded-2xl p-12 text-center border border-gray-200 space-y-4">
          <Bookmark className="w-12 h-12 text-gray-300 mx-auto" />
          <p className="text-gray-500 text-sm">You haven't bookmarked any schemes yet.</p>
          <Link
            to="/"
            className="inline-flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs px-4 py-2 rounded-xl transition"
          >
            <span>Browse & Discover Schemes</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {savedSchemes.map((item) => (
            <div key={item.id} className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-indigo-50 text-indigo-700">
                    {item.state || 'Central'}
                  </span>
                  <span className="text-xs text-gray-400">
                    Saved {new Date(item.saved_at).toLocaleDateString()}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-gray-900 hover:text-indigo-600">
                  <Link to={`/schemes/${item.scheme_id}`}>{item.scheme_name}</Link>
                </h3>
                {item.category && (
                  <p className="text-xs text-gray-500 mt-1">{item.category}</p>
                )}
              </div>

              <div className="pt-3 border-t border-gray-100 flex items-center justify-between">
                <button
                  onClick={() => handleUnsave(item.scheme_id)}
                  className="text-xs text-rose-600 hover:text-rose-700 font-medium flex items-center gap-1"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Remove Bookmark</span>
                </button>
                <Link
                  to={`/schemes/${item.scheme_id}`}
                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                >
                  View Details →
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
