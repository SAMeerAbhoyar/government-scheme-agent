import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import api from '../services/api';
import { Layers, ArrowLeft, CheckCircle, XCircle, HelpCircle } from 'lucide-react';

export default function Compare() {
  const [searchParams] = useSearchParams();
  const rawIds = searchParams.get('ids');
  const [comparisonData, setComparisonData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!rawIds) {
      setLoading(false);
      return;
    }
    const schemeIds = rawIds.split(',').filter(Boolean);
    if (schemeIds.length < 2 || schemeIds.length > 4) {
      setError('Please select between 2 and 4 schemes to compare side-by-side.');
      setLoading(false);
      return;
    }

    loadComparison(schemeIds);
  }, [rawIds]);

  const loadComparison = async (schemeIds) => {
    setLoading(true);
    setError('');
    try {
      const res = await api.post('/schemes/compare', { scheme_ids: schemeIds });
      setComparisonData(res.data);
    } catch (err) {
      console.error('Failed to load comparison matrix:', err);
      setError('Failed to load scheme comparison. Please check that valid scheme IDs were provided.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="max-w-7xl mx-auto px-4 py-12 text-center text-gray-500">Loading side-by-side comparison matrix...</div>;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center border border-purple-200">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Side-by-Side Scheme Comparison Matrix</h1>
            <p className="text-xs text-gray-500">Factual comparison of eligibility criteria, benefits, and matched rule details</p>
          </div>
        </div>

        <Link
          to="/"
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-indigo-600 bg-white border border-gray-200 px-3 py-1.5 rounded-xl transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Discovery</span>
        </Link>
      </div>

      {/* Mandatory Disclaimer Box */}
      <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 text-xs text-amber-900 font-medium">
        ℹ️ {comparisonData?.note || "Comparison matrix provides factual rule evaluations without ranking or declaring any single scheme as best."}
      </div>

      {error ? (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 p-4 rounded-xl text-xs">
          {error}
        </div>
      ) : !comparisonData || comparisonData.comparison.length === 0 ? (
        <div className="bg-white p-12 text-center rounded-2xl border border-gray-200 text-gray-500 text-sm">
          No schemes selected for comparison. Go to the Dashboard, check "Compare" on 2 to 4 scheme cards, and click Side-by-Side Compare.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-gray-200 text-left">
                <th className="p-4 w-1/5 font-bold text-gray-700 uppercase tracking-wider">Feature / Attribute</th>
                {comparisonData.comparison.map(item => (
                  <th key={item.scheme_id} className="p-4 w-1/4 font-bold text-gray-900 border-l border-gray-200">
                    <Link to={`/schemes/${item.scheme_id}`} className="text-indigo-600 hover:underline text-sm block font-bold mb-1">
                      {item.name}
                    </Link>
                    <span className="text-[10px] text-gray-500 block font-normal">{item.department || 'Government Scheme'}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              <tr>
                <td className="p-4 font-semibold text-gray-700 bg-slate-50">Jurisdiction & Category</td>
                {comparisonData.comparison.map(item => (
                  <td key={item.scheme_id} className="p-4 border-l border-gray-200">
                    <div className="space-y-1">
                      <span className="inline-block px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 font-semibold">{item.state || 'Central'}</span>
                      {item.category && <p className="text-gray-600">{item.category}</p>}
                    </div>
                  </td>
                ))}
              </tr>

              <tr>
                <td className="p-4 font-semibold text-gray-700 bg-slate-50">Deterministic Match Status</td>
                {comparisonData.comparison.map(item => (
                  <td key={item.scheme_id} className="p-4 border-l border-gray-200">
                    <span className={`inline-block px-2.5 py-1 rounded font-bold ${
                      item.match_status === 'potentially_relevant' ? 'bg-emerald-100 text-emerald-800' :
                      item.match_status === 'cannot_determine' ? 'bg-amber-100 text-amber-800' : 'bg-gray-200 text-gray-700'
                    }`}>
                      {item.match_status}
                    </span>
                  </td>
                ))}
              </tr>

              <tr>
                <td className="p-4 font-semibold text-gray-700 bg-slate-50">Rule Pass / Fail Breakdown</td>
                {comparisonData.comparison.map(item => (
                  <td key={item.scheme_id} className="p-4 border-l border-gray-200">
                    <div className="flex items-center space-x-3">
                      <span className="text-emerald-700 font-semibold flex items-center gap-1">
                        <CheckCircle className="w-3.5 h-3.5" /> {item.matched_rules_count} Passed
                      </span>
                      <span className="text-rose-700 font-semibold flex items-center gap-1">
                        <XCircle className="w-3.5 h-3.5" /> {item.failed_rules_count} Failed
                      </span>
                      <span className="text-amber-700 font-semibold flex items-center gap-1">
                        <HelpCircle className="w-3.5 h-3.5" /> {item.unknown_rules_count} Missing
                      </span>
                    </div>
                  </td>
                ))}
              </tr>

              <tr>
                <td className="p-4 font-semibold text-gray-700 bg-slate-50">Key Benefits</td>
                {comparisonData.comparison.map(item => (
                  <td key={item.scheme_id} className="p-4 border-l border-gray-200 leading-relaxed text-gray-700">
                    {item.benefits || 'Financial assistance / Direct Benefit Transfer (DBT)'}
                  </td>
                ))}
              </tr>

              <tr>
                <td className="p-4 font-semibold text-gray-700 bg-slate-50">Rule Details</td>
                {comparisonData.comparison.map(item => (
                  <td key={item.scheme_id} className="p-4 border-l border-gray-200">
                    <ul className="space-y-1">
                      {item.rule_summary.map((r, idx) => (
                        <li key={idx} className="text-[11px] text-gray-600">
                          <strong>{r.field}:</strong> {r.op} {String(r.required_value)}
                          <span className={`ml-1 font-semibold ${r.result === 'match' ? 'text-emerald-600' : r.result === 'no_match' ? 'text-rose-600' : 'text-amber-600'}`}>
                            ({r.result})
                          </span>
                        </li>
                      ))}
                    </ul>
                  </td>
                ))}
              </tr>

              <tr>
                <td className="p-4 font-semibold text-gray-700 bg-slate-50">Official Links</td>
                {comparisonData.comparison.map(item => (
                  <td key={item.scheme_id} className="p-4 border-l border-gray-200">
                    {item.source_url ? (
                      <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline font-medium">
                        Official Portal ↗
                      </a>
                    ) : (
                      <span className="text-gray-400">N/A</span>
                    )}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
