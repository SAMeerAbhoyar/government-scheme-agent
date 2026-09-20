import React, { useState, useEffect } from 'react';
import {
  Shield, BarChart2, CheckCircle, XCircle, AlertTriangle, RefreshCw, Edit3, Heart, Activity, FileText
} from 'lucide-react';
import api from '../services/api';

const AdminDashboard = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [overview, setOverview] = useState(null);
  const [unverified, setUnverified] = useState([]);
  const [changes, setChanges] = useState([]);
  const [health, setHealth] = useState([]);
  const [feedback, setFeedback] = useState([]);
  const [loading, setLoading] = useState(true);
  const [ingesting, setIngesting] = useState(false);
  const [editingScheme, setEditingScheme] = useState(null);
  const [editRulesJson, setEditRulesJson] = useState('');
  const [actionMsg, setActionMsg] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const [ovRes, uvRes, chRes, hlRes, fbRes] = await Promise.all([
        api.get('/admin/overview'),
        api.get('/admin/unverified'),
        api.get('/admin/changes'),
        api.get('/admin/source-health'),
        api.get('/admin/feedback')
      ]);
      setOverview(ovRes.data);
      setUnverified(uvRes.data);
      setChanges(chRes.data);
      setHealth(hlRes.data);
      setFeedback(fbRes.data);
    } catch (err) {
      console.error('Failed to load admin data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleVerify = async (id) => {
    try {
      await api.post(`/admin/schemes/${id}/verify`);
      setActionMsg('Scheme verified successfully!');
      loadData();
    } catch (err) {
      alert('Verification failed');
    }
  };

  const handleReject = async (id) => {
    try {
      await api.post(`/admin/schemes/${id}/reject`);
      setActionMsg('Scheme rejected.');
      loadData();
    } catch (err) {
      alert('Rejection failed');
    }
  };

  const handleSaveRules = async (id) => {
    try {
      const parsed = JSON.parse(editRulesJson);
      await api.post(`/admin/schemes/${id}/edit-rules`, { eligibility_rules: parsed });
      setEditingScheme(null);
      setActionMsg('Rules updated.');
      loadData();
    } catch (err) {
      alert('Invalid JSON or update failed');
    }
  };

  const handleIngestNow = async () => {
    setIngesting(true);
    try {
      const res = await api.post('/admin/ingest-now');
      setActionMsg(res.data.message || 'Ingestion started.');
      loadData();
    } catch (err) {
      alert('Manual ingestion failed.');
    } finally {
      setIngesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2.5">
            <Shield className="w-7 h-7 text-indigo-600" />
            Admin Command Center
          </h1>
          <p className="text-slate-600 text-sm mt-1">
            System metrics, extraction verification queue, change audits & crawler health.
          </p>
        </div>

        <button
          onClick={handleIngestNow}
          disabled={ingesting}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm px-4 py-2.5 rounded-xl shadow-sm transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${ingesting ? 'animate-spin' : ''}`} />
          {ingesting ? 'Running Ingestion...' : 'Run Ingestion Now'}
        </button>
      </div>

      {actionMsg && (
        <div className="mb-6 bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl text-sm flex justify-between">
          <span>{actionMsg}</span>
          <button onClick={() => setActionMsg('')} className="font-bold">×</button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-200 space-x-6 mb-8 overflow-x-auto">
        {[
          { id: 'overview', label: 'Overview', icon: BarChart2 },
          { id: 'unverified', label: `Unverified Queue (${unverified.length})`, icon: AlertTriangle },
          { id: 'changes', label: 'Changes Feed', icon: FileText },
          { id: 'health', label: 'Source Health', icon: Activity },
          { id: 'feedback', label: 'Feedback', icon: Heart },
        ].map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 pb-3 font-semibold text-sm border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Active Schemes</span>
              <p className="text-3xl font-extrabold text-slate-900 mt-2">{overview?.schemes_by_status?.active || 0}</p>
            </div>
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Unverified Queue</span>
              <p className="text-3xl font-extrabold text-amber-600 mt-2">{overview?.unverified_count || 0}</p>
            </div>
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Expired / Outdated</span>
              <p className="text-3xl font-extrabold text-slate-400 mt-2">
                {(overview?.schemes_by_status?.expired || 0) + (overview?.schemes_by_status?.outdated || 0)}
              </p>
            </div>
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Last Run Ingested</span>
              <p className="text-3xl font-extrabold text-indigo-600 mt-2">{overview?.last_run?.fetched || 0}</p>
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
            <h3 className="text-base font-bold text-slate-900 mb-4">Last Ingestion Run Summary</h3>
            {overview?.last_run ? (
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                <div><span className="text-slate-500 block text-xs">Source</span> <span className="font-semibold">{overview.last_run.source}</span></div>
                <div><span className="text-slate-500 block text-xs">Fetched</span> <span className="font-semibold text-emerald-600">{overview.last_run.fetched}</span></div>
                <div><span className="text-slate-500 block text-xs">Extracted</span> <span className="font-semibold text-blue-600">{overview.last_run.extracted}</span></div>
                <div><span className="text-slate-500 block text-xs">Flagged</span> <span className="font-semibold text-amber-600">{overview.last_run.flagged}</span></div>
                <div><span className="text-slate-500 block text-xs">Rejected</span> <span className="font-semibold text-rose-600">{overview.last_run.rejected}</span></div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">No ingestion runs logged yet.</p>
            )}
          </div>
        </div>
      )}

      {/* Unverified Tab */}
      {activeTab === 'unverified' && (
        <div className="space-y-6">
          {unverified.length === 0 ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500">
              No unverified schemes in the queue.
            </div>
          ) : (
            unverified.map(s => (
              <div key={s.id} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-lg font-bold text-slate-900">{s.name}</h3>
                    <span className="text-xs text-slate-500">{s.state} • {s.category || 'General'}</span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleVerify(s.id)}
                      className="flex items-center gap-1 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-3 py-1.5 rounded-lg"
                    >
                      <CheckCircle className="w-3.5 h-3.5" /> Verify
                    </button>
                    <button
                      onClick={() => {
                        setEditingScheme(s);
                        setEditRulesJson(JSON.stringify(s.eligibility_rules, null, 2));
                      }}
                      className="flex items-center gap-1 text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold px-3 py-1.5 rounded-lg"
                    >
                      <Edit3 className="w-3.5 h-3.5" /> Edit Rules
                    </button>
                    <button
                      onClick={() => handleReject(s.id)}
                      className="flex items-center gap-1 text-xs bg-rose-50 hover:bg-rose-100 text-rose-700 font-bold px-3 py-1.5 rounded-lg"
                    >
                      <XCircle className="w-3.5 h-3.5" /> Reject
                    </button>
                  </div>
                </div>

                {/* Side by side comparison */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs bg-slate-50 p-4 rounded-xl">
                  <div>
                    <span className="font-bold text-slate-700 block mb-1 uppercase tracking-wider">Source Quotes / Links</span>
                    <p className="text-slate-600 break-all">{s.source_url}</p>
                    {s.benefits && (
                      <p className="text-slate-600 mt-2"><strong>Benefits:</strong> {s.benefits}</p>
                    )}
                  </div>
                  <div>
                    <span className="font-bold text-slate-700 block mb-1 uppercase tracking-wider">Extracted Rules JSON</span>
                    <pre className="bg-slate-900 text-slate-100 p-3 rounded-lg text-[11px] overflow-x-auto max-h-48">
                      {JSON.stringify(s.eligibility_rules, null, 2)}
                    </pre>
                  </div>
                </div>

                {/* Edit Modal / Box */}
                {editingScheme?.id === s.id && (
                  <div className="mt-4 p-4 border border-indigo-200 rounded-xl bg-indigo-50/50 space-y-3">
                    <span className="font-bold text-xs text-indigo-900">Edit Eligibility Rules JSON:</span>
                    <textarea
                      value={editRulesJson}
                      onChange={e => setEditRulesJson(e.target.value)}
                      rows={6}
                      className="w-full font-mono text-xs p-3 rounded-lg border border-slate-300 bg-white"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleSaveRules(s.id)}
                        className="bg-indigo-600 text-white font-bold text-xs px-3 py-1.5 rounded-lg"
                      >
                        Save Rules
                      </button>
                      <button
                        onClick={() => setEditingScheme(null)}
                        className="bg-slate-200 text-slate-700 font-bold text-xs px-3 py-1.5 rounded-lg"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* Changes Feed Tab */}
      {activeTab === 'changes' && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
          <h3 className="text-base font-bold text-slate-900">Scheme Changes Feed</h3>
          {changes.length === 0 ? (
            <p className="text-sm text-slate-500">No version changes recorded yet.</p>
          ) : (
            changes.map(c => (
              <div key={c.id} className="p-4 border border-slate-100 rounded-xl bg-slate-50 text-xs space-y-2">
                <div className="flex justify-between font-semibold text-slate-800">
                  <span>{c.scheme_name}</span>
                  <span className="text-slate-400">{new Date(c.detected_at).toLocaleString()}</span>
                </div>
                <pre className="bg-slate-900 text-emerald-400 p-3 rounded-lg overflow-x-auto">
                  {JSON.stringify(c.diff, null, 2)}
                </pre>
              </div>
            ))
          )}
        </div>
      )}

      {/* Source Health Tab */}
      {activeTab === 'health' && (
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 text-slate-700 font-bold uppercase tracking-wider border-b">
              <tr>
                <th className="p-4">Scheme Name</th>
                <th className="p-4">Source URL</th>
                <th className="p-4">Failures</th>
                <th className="p-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {health.map(h => (
                <tr key={h.scheme_id} className="hover:bg-slate-50">
                  <td className="p-4 font-semibold text-slate-900">{h.scheme_name}</td>
                  <td className="p-4 text-slate-500 break-all">{h.source_url}</td>
                  <td className="p-4 font-bold text-rose-600">{h.consecutive_fetch_failures}</td>
                  <td className="p-4">
                    <span className={`px-2 py-0.5 rounded-full font-bold ${
                      h.status === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                    }`}>
                      {h.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Feedback Tab */}
      {activeTab === 'feedback' && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
          <h3 className="text-base font-bold text-slate-900">User Feedback Log</h3>
          {feedback.length === 0 ? (
            <p className="text-sm text-slate-500">No feedback entries recorded.</p>
          ) : (
            feedback.map(f => (
              <div key={f.id} className="p-4 rounded-xl border border-slate-100 bg-slate-50 text-xs flex justify-between">
                <div>
                  <span className="font-bold text-slate-800">{f.user_name} ({f.user_email})</span>
                  <p className="text-slate-600 mt-1">{f.comment || 'No comment provided'}</p>
                </div>
                <span className={`font-bold px-2 py-1 h-fit rounded ${f.useful ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'}`}>
                  {f.useful ? '👍 Useful' : '👎 Not Useful'}
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
