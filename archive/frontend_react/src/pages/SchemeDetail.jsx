import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../services/api';
import { ArrowLeft, ShieldCheck, ExternalLink, ThumbsUp, ThumbsDown, Bookmark, Check, X, HelpCircle } from 'lucide-react';

export default function SchemeDetail() {
  const { id } = useParams();
  const [scheme, setScheme] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [feedbackUseful, setFeedbackUseful] = useState(null);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  useEffect(() => {
    loadScheme();
  }, [id]);

  const loadScheme = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get(`/schemes/${id}`);
      setScheme(res.data);
      setIsSaved(res.data.is_saved || false);
    } catch (err) {
      console.error('Failed to load scheme details:', err);
      setError('Failed to load scheme details. Scheme might not exist.');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleSave = async () => {
    try {
      if (isSaved) {
        await api.delete(`/schemes/${id}/save`);
        setIsSaved(false);
      } else {
        await api.post(`/schemes/${id}/save`);
        setIsSaved(true);
      }
    } catch (err) {
      console.error('Failed to toggle save:', err);
    }
  };

  const handleFeedbackSubmit = async (e) => {
    e.preventDefault();
    if (feedbackUseful === null) return;

    try {
      await api.post('/recommendations/feedback', {
        scheme_id: id,
        useful: feedbackUseful,
        comment: feedbackComment
      });
      setFeedbackSubmitted(true);
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    }
  };

  if (loading) {
    return <div className="max-w-7xl mx-auto px-4 py-12 text-center text-gray-500">Loading scheme details...</div>;
  }

  if (error || !scheme) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center">
        <p className="text-rose-600 text-sm mb-4">{error || 'Scheme not found'}</p>
        <Link to="/" className="text-indigo-600 font-semibold text-xs hover:underline">← Return to Dashboard</Link>
      </div>
    );
  }

  const match = scheme.user_match;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Navigation */}
      <div className="flex items-center justify-between">
        <Link
          to="/"
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-indigo-600 bg-white border border-gray-200 px-3 py-1.5 rounded-xl transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Schemes</span>
        </Link>

        <button
          onClick={handleToggleSave}
          className={`px-4 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition ${
            isSaved ? 'bg-amber-100 text-amber-800 border border-amber-300' : 'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50'
          }`}
        >
          <Bookmark className={`w-4 h-4 ${isSaved ? 'fill-current text-amber-600' : ''}`} />
          <span>{isSaved ? 'Bookmarked' : 'Save Bookmark'}</span>
        </button>
      </div>

      {/* Main Header */}
      <div className="bg-white rounded-2xl border border-gray-200 p-8 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="px-3 py-1 bg-indigo-50 text-indigo-700 font-bold text-xs rounded-full">
            {scheme.state || 'Central'}
          </span>
          {scheme.category && (
            <span className="px-3 py-1 bg-blue-50 text-blue-700 font-semibold text-xs rounded-full">
              {scheme.category}
            </span>
          )}
          {scheme.status === 'unverified' ? (
            <span className="px-3 py-1 bg-rose-100 text-rose-800 font-semibold text-xs rounded-full border border-rose-200">
              Unverified Official Scheme
            </span>
          ) : (
            <span className="px-3 py-1 bg-emerald-100 text-emerald-800 font-semibold text-xs rounded-full border border-emerald-200 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" /> Verified Official Scheme
            </span>
          )}
          {scheme.extraction_confidence && (
            <span className="text-[10px] text-gray-400 font-mono">
              Extraction Confidence: {Math.round(scheme.extraction_confidence * 100)}%
            </span>
          )}
        </div>

        <h1 className="text-3xl font-extrabold text-gray-900 leading-tight">{scheme.name}</h1>
        {scheme.department && (
          <p className="text-sm font-medium text-gray-500">{scheme.department}</p>
        )}

        <div className="pt-4 border-t border-gray-100 flex flex-wrap gap-4 items-center text-xs">
          {scheme.source_url && (
            <a
              href={scheme.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 font-semibold text-indigo-600 hover:text-indigo-800"
            >
              <span>Official Government Portal</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
          {scheme.application_url && scheme.application_url !== scheme.source_url && (
            <a
              href={scheme.application_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 font-semibold text-emerald-600 hover:text-emerald-800"
            >
              <span>Apply Online Portal</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>

      {/* User Eligibility Evaluation */}
      {match && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <h2 className="text-lg font-bold text-gray-900">Your Eligibility Evaluation</h2>
            <span className={`px-3 py-1 rounded-full text-xs font-bold ${
              match.status === 'potentially_relevant' ? 'bg-emerald-100 text-emerald-800' :
              match.status === 'cannot_determine' ? 'bg-amber-100 text-amber-800' : 'bg-gray-200 text-gray-700'
            }`}>
              {match.status}
            </span>
          </div>

          <div className="space-y-2">
            {match.rule_results?.map((r, idx) => (
              <div key={idx} className="flex items-center space-x-2 text-xs py-1 border-b border-gray-50 last:border-0">
                {r.result === 'match' && <Check className="w-4 h-4 text-emerald-600 font-bold" />}
                {r.result === 'no_match' && <X className="w-4 h-4 text-rose-600 font-bold" />}
                {r.result === 'unknown' && <HelpCircle className="w-4 h-4 text-amber-500 font-bold" />}
                <span className="font-semibold text-gray-800">{r.field.replace('_', ' ').toUpperCase()}:</span>
                <span className="text-gray-600">Requires {r.op} {String(r.required_value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Scheme Description & Benefits */}
      <div className="bg-white rounded-2xl border border-gray-200 p-8 shadow-sm space-y-6">
        <div>
          <h2 className="text-lg font-bold text-gray-900 mb-2">Scheme Overview</h2>
          <p className="text-sm text-gray-700 leading-relaxed">{scheme.summary || 'No overview text extracted.'}</p>
        </div>

        {scheme.benefits && (
          <div className="pt-4 border-t border-gray-100">
            <h2 className="text-lg font-bold text-gray-900 mb-2">Key Benefits</h2>
            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">{scheme.benefits}</p>
          </div>
        )}

        {scheme.eligibility_summary && (
          <div className="pt-4 border-t border-gray-100">
            <h2 className="text-lg font-bold text-gray-900 mb-2">Summary of Eligibility Criteria</h2>
            <p className="text-sm text-gray-700 leading-relaxed">{scheme.eligibility_summary}</p>
          </div>
        )}

        {scheme.documents_required && (
          <div className="pt-4 border-t border-gray-100">
            <h2 className="text-lg font-bold text-gray-900 mb-2">Documents Required</h2>
            <p className="text-sm text-gray-700 leading-relaxed">{scheme.documents_required}</p>
          </div>
        )}

        {scheme.application_process && (
          <div className="pt-4 border-t border-gray-100">
            <h2 className="text-lg font-bold text-gray-900 mb-2">Application Procedure</h2>
            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">{scheme.application_process}</p>
          </div>
        )}
      </div>

      {/* User Feedback Form */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm space-y-4">
        <h3 className="text-base font-bold text-gray-900">Provide Feedback on this Recommendation</h3>
        {feedbackSubmitted ? (
          <div className="p-3 bg-emerald-50 text-emerald-800 rounded-xl text-xs font-semibold">
            Thank you for your feedback! Your response helps refine our grounding and matching algorithms.
          </div>
        ) : (
          <form onSubmit={handleFeedbackSubmit} className="space-y-4">
            <div className="flex items-center space-x-4 text-xs font-semibold">
              <span>Is this scheme match helpful?</span>
              <button
                type="button"
                onClick={() => setFeedbackUseful(true)}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg border transition ${
                  feedbackUseful === true ? 'bg-emerald-100 text-emerald-800 border-emerald-300 font-bold' : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                }`}
              >
                <ThumbsUp className="w-3.5 h-3.5" /> Yes
              </button>
              <button
                type="button"
                onClick={() => setFeedbackUseful(false)}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg border transition ${
                  feedbackUseful === false ? 'bg-rose-100 text-rose-800 border-rose-300 font-bold' : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                }`}
              >
                <ThumbsDown className="w-3.5 h-3.5" /> No
              </button>
            </div>

            {feedbackUseful !== null && (
              <div className="space-y-2">
                <textarea
                  rows="2"
                  placeholder="Optional comments or suggestions..."
                  value={feedbackComment}
                  onChange={(e) => setFeedbackComment(e.target.value)}
                  className="w-full text-xs p-2 border border-gray-300 rounded-xl focus:ring-indigo-500 focus:border-indigo-500"
                ></textarea>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-xl transition"
                >
                  Submit Feedback
                </button>
              </div>
            )}
          </form>
        )}
      </div>
    </div>
  );
}
