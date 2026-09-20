import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';

export default function SchemeResultCard({
  match,
  onProfileUpdated,
  isSaved = false,
  onToggleSave,
  isSelectedForCompare = false,
  onToggleSelectCompare
}) {
  const [answers, setAnswers] = useState({});
  const [isSubmittingAnswers, setIsSubmittingAnswers] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState(null);

  const handleInputChange = (field, value) => {
    setAnswers(prev => ({ ...prev, [field]: value }));
  };

  const handleAnswerSubmit = async (e) => {
    e.preventDefault();
    if (Object.keys(answers).length === 0) return;

    setIsSubmittingAnswers(true);
    try {
      await api.post('/profile/answers', answers);
      setAnswers({});
      if (onProfileUpdated) onProfileUpdated();
    } catch (err) {
      console.error('Failed to submit answers:', err);
    } finally {
      setIsSubmittingAnswers(false);
    }
  };

  const handleFeedback = async (useful) => {
    try {
      await api.post('/recommendations/feedback', {
        scheme_id: match.scheme_id,
        useful: useful
      });
      setFeedbackGiven(useful);
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'potentially_relevant':
        return <span className="bg-emerald-100 text-emerald-800 text-xs font-semibold px-2.5 py-0.5 rounded border border-emerald-300">Potentially Relevant</span>;
      case 'cannot_determine':
        return <span className="bg-amber-100 text-amber-800 text-xs font-semibold px-2.5 py-0.5 rounded border border-amber-300">Needs Information</span>;
      case 'not_matching':
        return <span className="bg-gray-100 text-gray-700 text-xs font-semibold px-2.5 py-0.5 rounded border border-gray-300">Not Matching</span>;
      default:
        return null;
    }
  };

  return (
    <div className={`bg-white rounded-xl shadow-md hover:shadow-lg transition border ${isSelectedForCompare ? 'border-indigo-500 ring-2 ring-indigo-200' : 'border-gray-200'} p-6 flex flex-col justify-between space-y-4`}>
      {/* Header & Badges */}
      <div>
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center space-x-2 flex-wrap gap-y-1 mb-1">
              {getStatusBadge(match.status)}
              {match.unverified && (
                <span className="bg-rose-100 text-rose-800 text-xs font-medium px-2 py-0.5 rounded border border-rose-300">Unverified Official Scheme</span>
              )}
              {match.state && (
                <span className="bg-indigo-50 text-indigo-700 text-xs font-medium px-2 py-0.5 rounded">{match.state}</span>
              )}
              {match.category && (
                <span className="bg-blue-50 text-blue-700 text-xs font-medium px-2 py-0.5 rounded">{match.category}</span>
              )}
            </div>
            <h3 className="text-xl font-bold text-gray-900 hover:text-indigo-600">
              <Link to={`/schemes/${match.scheme_id}`}>{match.scheme_name}</Link>
            </h3>
            {match.department && (
              <p className="text-xs text-gray-500 font-medium">{match.department}</p>
            )}
          </div>

          <div className="flex items-center space-x-2">
            {onToggleSelectCompare && (
              <label className="flex items-center space-x-1 text-xs text-gray-600 cursor-pointer bg-gray-50 px-2 py-1 rounded border hover:bg-gray-100">
                <input
                  type="checkbox"
                  checked={isSelectedForCompare}
                  onChange={() => onToggleSelectCompare(match.scheme_id)}
                  className="rounded text-indigo-600 focus:ring-indigo-500"
                />
                <span>Compare</span>
              </label>
            )}
            {onToggleSave && (
              <button
                onClick={() => onToggleSave(match.scheme_id, isSaved)}
                className={`p-1.5 rounded-full transition ${isSaved ? 'text-amber-500 bg-amber-50 hover:bg-amber-100' : 'text-gray-400 hover:text-amber-500 hover:bg-gray-100'}`}
                title={isSaved ? "Remove Bookmark" : "Save Scheme"}
              >
                <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24">
                  <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* AI Grounded Explanation */}
        {match.explanation && (
          <div className="mt-3 bg-slate-50 rounded-lg p-3 border border-slate-200">
            <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-700 mb-1">
              <svg className="w-4 h-4 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>AI Grounded Explanation:</span>
            </div>
            <p className="text-sm text-gray-700 whitespace-pre-line leading-relaxed">{match.explanation}</p>
          </div>
        )}

        {/* Disclaimer */}
        <p className="mt-2 text-xs text-gray-400 italic">
          {match.disclaimer}
        </p>

        {/* Deterministic Rule Evaluation Results */}
        {match.rule_results && match.rule_results.length > 0 && (
          <div className="mt-4 space-y-2">
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Eligibility Rule Analysis</h4>
            <div className="space-y-1">
              {match.rule_results.map((rule, idx) => (
                <div key={idx} className="flex items-start text-xs space-x-2 py-1 border-b border-gray-100 last:border-0">
                  {rule.result === 'match' && (
                    <span className="text-emerald-600 font-bold flex-shrink-0">✓</span>
                  )}
                  {rule.result === 'no_match' && (
                    <span className="text-rose-600 font-bold flex-shrink-0">✕</span>
                  )}
                  {rule.result === 'unknown' && (
                    <span className="text-amber-500 font-bold flex-shrink-0">?</span>
                  )}
                  <div className="flex-grow">
                    <span className="font-medium text-gray-800">{rule.field.replace('_', ' ').toUpperCase()}: </span>
                    <span className="text-gray-600">
                      Requires {rule.op} {String(rule.required_value)}
                      {rule.user_value !== null && rule.user_value !== undefined && (
                        <span> (Your profile: <strong className="text-gray-900">{String(rule.user_value)}</strong>)</span>
                      )}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Missing Info Interactive Questions */}
        {match.missing_questions && match.missing_questions.length > 0 && (
          <div className="mt-4 bg-amber-50 border border-amber-200 rounded-lg p-3">
            <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wider mb-2">
              Missing Profile Information ({match.missing_questions.length})
            </h4>
            <form onSubmit={handleAnswerSubmit} className="space-y-3">
              {match.missing_questions.map((q) => (
                <div key={q.field} className="text-xs">
                  <label className="block text-gray-700 font-medium mb-1">{q.question_text}</label>
                  {q.input_type === 'select' && q.options ? (
                    <select
                      value={answers[q.field] ?? ''}
                      onChange={(e) => handleInputChange(q.field, e.target.value)}
                      className="w-full text-xs p-1.5 border border-gray-300 rounded focus:ring-amber-500 focus:border-amber-500"
                    >
                      <option value="">Select option...</option>
                      {q.options.map(opt => (
                        <option key={String(opt.value)} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={q.input_type === 'number' ? 'number' : 'text'}
                      placeholder={q.placeholder || 'Enter value'}
                      value={answers[q.field] ?? ''}
                      onChange={(e) => handleInputChange(q.field, e.target.value)}
                      className="w-full text-xs p-1.5 border border-gray-300 rounded focus:ring-amber-500 focus:border-amber-500"
                    />
                  )}
                </div>
              ))}
              <button
                type="submit"
                disabled={isSubmittingAnswers || Object.keys(answers).length === 0}
                className="w-full bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs py-1.5 rounded transition disabled:opacity-50"
              >
                {isSubmittingAnswers ? 'Updating Profile...' : 'Save & Re-evaluate Eligibility'}
              </button>
            </form>
          </div>
        )}
      </div>

      {/* Footer & Actions */}
      <div className="pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center space-x-3">
          <span>Was this helpful?</span>
          <button
            onClick={() => handleFeedback(true)}
            className={`px-2 py-0.5 rounded border transition ${feedbackGiven === true ? 'bg-emerald-100 text-emerald-800 border-emerald-300 font-bold' : 'hover:bg-gray-100 text-gray-600'}`}
          >
            👍 Yes
          </button>
          <button
            onClick={() => handleFeedback(false)}
            className={`px-2 py-0.5 rounded border transition ${feedbackGiven === false ? 'bg-rose-100 text-rose-800 border-rose-300 font-bold' : 'hover:bg-gray-100 text-gray-600'}`}
          >
            👎 No
          </button>
        </div>

        <div className="flex items-center space-x-3">
          {match.source_url && (
            <a
              href={match.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-500 hover:text-indigo-600 font-medium"
            >
              Official Source ↗
            </a>
          )}
          <Link
            to={`/schemes/${match.scheme_id}`}
            className="bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold px-3 py-1.5 rounded transition"
          >
            View Details
          </Link>
        </div>
      </div>
    </div>
  );
}
