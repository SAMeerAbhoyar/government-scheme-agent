import React, { useContext, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import api from '../services/api';
import SchemeResultCard from '../components/SchemeResultCard';
import { Search, Sparkles, User, ShieldCheck, ArrowRight, Layers, Bookmark } from 'lucide-react';

const Dashboard = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState('query'); // 'query' | 'profile'
  const [profile, setProfile] = useState(null);
  
  // Mode 1 Query States
  const [searchQuery, setSearchQuery] = useState('');
  const [stateFilter, setStateFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  
  // Results
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Bookmarks state
  const [savedSchemeIds, setSavedSchemeIds] = useState(new Set());
  // Compare selection state
  const [selectedForCompare, setSelectedForCompare] = useState(new Set());

  useEffect(() => {
    loadProfileAndBookmarks();
  }, []);

  const loadProfileAndBookmarks = async () => {
    try {
      const [profRes, savedRes] = await Promise.all([
        api.get('/profile'),
        api.get('/schemes/saved').catch(() => ({ data: [] }))
      ]);
      setProfile(profRes.data);
      const savedIds = new Set(savedRes.data.map(s => String(s.scheme_id)));
      setSavedSchemeIds(savedIds);
    } catch (e) {
      console.error('Failed to fetch initial profile/bookmarks', e);
    }
  };

  const handleQueryDiscover = async (e) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError('');
    try {
      const res = await api.post('/discover/query', {
        query: searchQuery,
        state_filter: stateFilter || null,
        category_filter: categoryFilter || null
      });
      setResults(res.data);
    } catch (err) {
      console.error('Query discovery failed:', err);
      setError('Failed to search schemes. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleProfileDiscover = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.post('/discover/profile', {
        state_filter: stateFilter || null,
        category_filter: categoryFilter || null
      });
      setResults(res.data);
    } catch (err) {
      console.error('Profile discovery failed:', err);
      setError('Failed to run AI Profile Matcher. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleSave = async (schemeId, currentIsSaved) => {
    try {
      if (currentIsSaved) {
        await api.delete(`/schemes/${schemeId}/save`);
        setSavedSchemeIds(prev => {
          const next = new Set(prev);
          next.delete(schemeId);
          return next;
        });
      } else {
        await api.post(`/schemes/${schemeId}/save`);
        setSavedSchemeIds(prev => new Set(prev).add(schemeId));
      }
    } catch (err) {
      console.error('Failed to toggle save:', err);
    }
  };

  const handleToggleSelectCompare = (schemeId) => {
    setSelectedForCompare(prev => {
      const next = new Set(prev);
      if (next.has(schemeId)) {
        next.delete(schemeId);
      } else {
        if (next.size >= 4) {
          alert('You can compare a maximum of 4 schemes at once.');
          return prev;
        }
        next.add(schemeId);
      }
      return next;
    });
  };

  const handleGoToCompare = () => {
    if (selectedForCompare.size < 2) return;
    const ids = Array.from(selectedForCompare).join(',');
    navigate(`/compare?ids=${ids}`);
  };

  const getProfileCompletion = () => {
    if (!profile) return 0;
    const fields = [
      'age', 'gender', 'state', 'district', 'education_level',
      'occupation', 'annual_income', 'social_category'
    ];
    const filled = fields.filter((f) => profile[f] !== null && profile[f] !== '');
    return Math.round((filled.length / fields.length) * 100);
  };

  const completion = getProfileCompletion();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 pb-24">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-indigo-700 via-indigo-600 to-blue-700 rounded-3xl p-8 text-white shadow-xl relative overflow-hidden">
        <div className="absolute -right-10 -bottom-10 w-64 h-64 bg-white/10 rounded-full blur-2xl pointer-events-none"></div>
        <div className="max-w-3xl space-y-3 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/15 backdrop-blur-md text-xs font-semibold text-indigo-100 border border-white/20">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-300" />
            Phase 3 Active • Hybrid RAG & Deterministic Rule Matching Engine
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Namaste, {user?.name || 'Citizen'}!
          </h1>
          <p className="text-indigo-100 text-sm sm:text-base leading-relaxed">
            Discover official Central & Maharashtra government schemes tailored precisely to your profile with zero hallucinations and verified source links.
          </p>
        </div>
      </div>

      {/* Profile Completion Alert */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shrink-0">
            <User className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-bold text-slate-900 text-base">Citizen Profile Completion</h2>
              <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-indigo-100 text-indigo-800 border border-indigo-200">
                {completion}% Complete
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
              {completion < 50
                ? 'Fill in income, category, and state details in your profile for accurate deterministic eligibility checks.'
                : 'Your profile has sufficient information for deterministic rule matching!'}
            </p>
          </div>
        </div>
        <Link
          to="/profile"
          className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs sm:text-sm rounded-xl transition shadow shrink-0 flex items-center gap-1.5"
        >
          <span>Update Profile</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Mode Selection Tabs */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-200 pb-4 gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Select Scheme Discovery Mode</h2>
            <p className="text-xs text-slate-500">Both discovery modes share the exact same deterministic eligibility rule evaluator</p>
          </div>

          <div className="flex bg-slate-100 p-1 rounded-xl">
            <button
              onClick={() => { setActiveTab('query'); setResults(null); }}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition ${activeTab === 'query' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
            >
              <Search className="w-4 h-4" />
              <span>Mode 1: Search Query</span>
            </button>
            <button
              onClick={() => { setActiveTab('profile'); setResults(null); }}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition ${activeTab === 'profile' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
            >
              <Sparkles className="w-4 h-4" />
              <span>Mode 2: AI Profile Matcher</span>
            </button>
          </div>
        </div>

        {/* Tab 1: Natural Query Search */}
        {activeTab === 'query' && (
          <form onSubmit={handleQueryDiscover} className="space-y-4">
            <div className="relative">
              <input
                type="text"
                placeholder="e.g. Scholarship for OBC student in Maharashtra with annual income under 2 lakhs"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full text-sm pl-11 pr-32 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 shadow-sm"
              />
              <Search className="w-5 h-5 text-slate-400 absolute left-3.5 top-3.5" />
              <button
                type="submit"
                disabled={loading || !searchQuery.trim()}
                className="absolute right-2 top-2 px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg transition disabled:opacity-50"
              >
                {loading ? 'Planning Query...' : 'Search Schemes'}
              </button>
            </div>

            {/* Optional Filter Overrides */}
            <div className="flex flex-wrap gap-4 items-center text-xs text-slate-600">
              <span className="font-semibold text-slate-700">Optional Filters:</span>
              <div className="flex items-center space-x-2">
                <label className="font-medium">State:</label>
                <select
                  value={stateFilter}
                  onChange={(e) => setStateFilter(e.target.value)}
                  className="p-1.5 border border-slate-300 rounded-lg text-xs"
                >
                  <option value="">All States / Central</option>
                  <option value="Maharashtra">Maharashtra</option>
                  <option value="Central">Central Govt Only</option>
                </select>
              </div>

              <div className="flex items-center space-x-2">
                <label className="font-medium">Category:</label>
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="p-1.5 border border-slate-300 rounded-lg text-xs"
                >
                  <option value="">All Categories</option>
                  <option value="Education">Education & Scholarships</option>
                  <option value="Agriculture">Agriculture & Farmers</option>
                  <option value="Housing">Housing & Urban</option>
                  <option value="Health">Health & Welfare</option>
                  <option value="Employment">Employment & Skill</option>
                </select>
              </div>
            </div>
          </form>
        )}

        {/* Tab 2: AI Profile Matcher */}
        {activeTab === 'profile' && (
          <div className="space-y-4">
            <p className="text-sm text-slate-600 leading-relaxed">
              Click below to automatically evaluate your active citizen profile against all ingested Central and Maharashtra government schemes in our offline database.
            </p>
            <div className="flex items-center space-x-4">
              <button
                onClick={handleProfileDiscover}
                disabled={loading}
                className="px-6 py-3 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 text-white font-bold text-sm rounded-xl shadow-md transition flex items-center gap-2 disabled:opacity-50"
              >
                <Sparkles className="w-4 h-4" />
                <span>{loading ? 'Evaluating Profile Match...' : 'Run AI Profile Scheme Matcher'}</span>
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-xl">
            {error}
          </div>
        )}
      </div>

      {/* Discovery Results */}
      {results && (
        <div className="space-y-6">
          {/* Query Plan Info Box */}
          {results.query_plan && (
            <div className="bg-indigo-50 border border-indigo-200 rounded-2xl p-4 text-xs text-indigo-900 space-y-1">
              <div className="font-bold flex items-center gap-1.5 text-indigo-950">
                <Sparkles className="w-4 h-4 text-indigo-600" />
                <span>Extracted Query Intent & Domain Filters:</span>
              </div>
              <div className="flex flex-wrap gap-4 mt-1">
                {results.query_plan.extracted_filters.state && (
                  <span><strong>State Filter:</strong> {results.query_plan.extracted_filters.state}</span>
                )}
                {results.query_plan.extracted_filters.category && (
                  <span><strong>Category Filter:</strong> {results.query_plan.extracted_filters.category}</span>
                )}
                <span><strong>Search Terms:</strong> {results.query_plan.search_terms?.join(', ')}</span>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-slate-900">
              Matched Schemes ({results.total_matches})
            </h3>
            <span className="text-xs text-slate-500 font-medium">
              Ranked by Eligibility Status & Deadline
            </span>
          </div>

          {results.matches.length === 0 ? (
            <div className="bg-white p-12 text-center rounded-2xl border border-slate-200">
              <p className="text-slate-500 text-sm">No schemes matched your criteria. Try updating your profile demographics or broadening search filters.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {results.matches.map((m) => (
                <SchemeResultCard
                  key={m.scheme_id}
                  match={m}
                  onProfileUpdated={() => {
                    if (activeTab === 'query') handleQueryDiscover();
                    else handleProfileDiscover();
                  }}
                  isSaved={savedSchemeIds.has(m.scheme_id)}
                  onToggleSave={handleToggleSave}
                  isSelectedForCompare={selectedForCompare.has(m.scheme_id)}
                  onToggleSelectCompare={handleToggleSelectCompare}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Floating Side-by-Side Compare Bar */}
      {selectedForCompare.size > 0 && (
        <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-slate-900 text-white px-6 py-3.5 rounded-full shadow-2xl z-50 flex items-center space-x-4 border border-slate-700">
          <span className="text-xs font-bold">
            {selectedForCompare.size} scheme{selectedForCompare.size > 1 ? 's' : ''} selected for comparison
          </span>
          <button
            onClick={handleGoToCompare}
            disabled={selectedForCompare.size < 2}
            className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-full transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Side-by-Side Compare</span>
          </button>
          <button
            onClick={() => setSelectedForCompare(new Set())}
            className="text-xs text-slate-400 hover:text-white"
          >
            Clear
          </button>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
