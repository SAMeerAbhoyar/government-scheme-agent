import React, { useState, useEffect, useContext } from 'react';
import api from '../services/api';
import { AuthContext } from '../context/AuthContext';
import { User, Briefcase, GraduationCap, Users, Save, CheckCircle2, AlertCircle, Trash2, ShieldAlert } from 'lucide-react';

const Profile = () => {
  const { logout } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [message, setMessage] = useState(null);

  const [profile, setProfile] = useState({
    age: '',
    gender: '',
    state: '',
    district: '',
    rural_urban: '',
    education_level: '',
    course: '',
    year: '',
    occupation: '',
    employment_status: '',
    annual_income: '',
    family_size: '',
    social_category: '',
    disability: '',
    minority: '',
    bpl_card: '',
    domicile_state: '',
    marital_status: '',
    land_holding_acres: '',
  });

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await api.get('/profile');
      const p = res.data;
      setProfile({
        age: p.age ?? '',
        gender: p.gender ?? '',
        state: p.state ?? '',
        district: p.district ?? '',
        rural_urban: p.rural_urban ?? '',
        education_level: p.education_level ?? '',
        course: p.course ?? '',
        year: p.year ?? '',
        occupation: p.occupation ?? '',
        employment_status: p.employment_status ?? '',
        annual_income: p.annual_income ?? '',
        family_size: p.family_size ?? '',
        social_category: p.social_category ?? '',
        disability: p.disability === null || p.disability === undefined ? '' : p.disability ? 'true' : 'false',
        minority: p.minority === null || p.minority === undefined ? '' : p.minority ? 'true' : 'false',
        bpl_card: p.bpl_card === null || p.bpl_card === undefined ? '' : p.bpl_card ? 'true' : 'false',
        domicile_state: p.domicile_state ?? '',
        marital_status: p.marital_status ?? '',
        land_holding_acres: p.land_holding_acres ?? '',
      });
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to load profile details.' });
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setProfile((prev) => ({ ...prev, [name]: value }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    const payload = {
      age: profile.age !== '' ? parseInt(profile.age) : null,
      gender: profile.gender !== '' ? profile.gender : null,
      state: profile.state !== '' ? profile.state : null,
      district: profile.district !== '' ? profile.district : null,
      rural_urban: profile.rural_urban !== '' ? profile.rural_urban : null,
      education_level: profile.education_level !== '' ? profile.education_level : null,
      course: profile.course !== '' ? profile.course : null,
      year: profile.year !== '' ? profile.year : null,
      occupation: profile.occupation !== '' ? profile.occupation : null,
      employment_status: profile.employment_status !== '' ? profile.employment_status : null,
      annual_income: profile.annual_income !== '' ? parseFloat(profile.annual_income) : null,
      family_size: profile.family_size !== '' ? parseInt(profile.family_size) : null,
      social_category: profile.social_category !== '' ? profile.social_category : null,
      disability: profile.disability === '' ? null : profile.disability === 'true',
      minority: profile.minority === '' ? null : profile.minority === 'true',
      bpl_card: profile.bpl_card === '' ? null : profile.bpl_card === 'true',
      domicile_state: profile.domicile_state !== '' ? profile.domicile_state : null,
      marital_status: profile.marital_status !== '' ? profile.marital_status : null,
      land_holding_acres: profile.land_holding_acres !== '' ? parseFloat(profile.land_holding_acres) : null,
    };

    try {
      await api.put('/profile', payload);
      setMessage({ type: 'success', text: 'Profile saved successfully! Deterministic eligibility evaluator updated.' });
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to update profile. Please verify your input.' });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
    setDeleting(true);
    try {
      await api.delete('/account');
      await logout();
      window.location.href = '/login';
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to delete account. Please try again.' });
      setDeleting(false);
      setShowDeleteModal(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-4 text-center text-slate-500">
        Loading citizen profile...
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <User className="w-6 h-6 text-brand-600" />
            Demographic & Citizen Profile
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Complete your profile to enable deterministic rule matching for Central & Maharashtra schemes.
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-5 py-2.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-semibold text-sm rounded-xl shadow border border-brand-500 flex items-center gap-2 transition-all cursor-pointer shrink-0"
        >
          <Save className="w-4 h-4" />
          {saving ? 'Saving...' : 'Save Profile'}
        </button>
      </div>

      {message && (
        <div
          className={`p-4 rounded-xl text-sm flex items-center gap-3 border ${
            message.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-red-50 border-red-200 text-red-800'
          }`}
        >
          {message.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
          )}
          <span>{message.text}</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Section 1: Personal Demographics */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
            <User className="w-5 h-5 text-brand-600" />
            Personal & Domicile
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Age (Years)</label>
              <input
                type="number"
                name="age"
                value={profile.age}
                onChange={handleChange}
                placeholder="Unknown"
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Gender</label>
              <select
                name="gender"
                value={profile.gender}
                onChange={handleChange}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 outline-none bg-white"
              >
                <option value="">Prefer not to say (Unknown)</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Transgender">Transgender</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Current State</label>
              <select
                name="state"
                value={profile.state}
                onChange={handleChange}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 outline-none bg-white"
              >
                <option value="">Unknown</option>
                <option value="Maharashtra">Maharashtra</option>
                <option value="Central">Central Govt Jurisdiction</option>
                <option value="Other">Other State</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">District</label>
              <input
                type="text"
                name="district"
                value={profile.district}
                onChange={handleChange}
                placeholder="e.g. Pune / Mumbai / Thane"
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Rural / Urban</label>
              <select
                name="rural_urban"
                value={profile.rural_urban}
                onChange={handleChange}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 outline-none bg-white"
              >
                <option value="">Unknown</option>
                <option value="Rural">Rural</option>
                <option value="Urban">Urban</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Marital Status</label>
              <select
                name="marital_status"
                value={profile.marital_status}
                onChange={handleChange}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 outline-none bg-white"
              >
                <option value="">Prefer not to say (Unknown)</option>
                <option value="Single">Single</option>
                <option value="Married">Married</option>
                <option value="Widowed">Widowed</option>
                <option value="Divorced">Divorced</option>
              </select>
            </div>
          </div>
        </div>

        {/* Section 2: Education */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
            <GraduationCap className="w-5 h-5 text-brand-600" />
            Education Details
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Education Level</label>
              <select
                name="education_level"
                value={profile.education_level}
                onChange={handleChange}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 outline-none bg-white"
              >
                <option value="">Unknown</option>
                <option value="10th Pass">10th Pass</option>
                <option value="12th Pass">12th Pass</option>
                <option value="Diploma">Diploma</option>
                <option value="Undergraduate">Undergraduate</option>
                <option value="Postgraduate">Postgraduate</option>
                <option value="Doctorate">Doctorate</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Course / Degree</label>
              <input
                type="text"
                name="course"
                value={profile.course}
                onChange={handleChange}
                placeholder="e.g. B.Tech / B.Sc / BA"
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Current Year / Status</label>
              <input
                type="text"
                name="year"
                value={profile.year}
                onChange={handleChange}
                placeholder="e.g. 1st Year / Completed"
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 outline-none"
              />
            </div>
          </div>
        </div>

        {/* Section 3: Financial & Employment */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
            <Briefcase className="w-5 h-5 text-brand-600" />
            Financial & Employment
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Occupation</label>
              <input
                type="text"
                name="occupation"
                value={profile.occupation}
                onChange={handleChange}
                placeholder="e.g. Student / Farmer / Self-employed"
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Annual Family Income (₹)</label>
              <input
                type="number"
                name="annual_income"
                value={profile.annual_income}
                onChange={handleChange}
                placeholder="Unknown"
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Family Member Count</label>
              <input
                type="number"
                name="family_size"
                value={profile.family_size}
                onChange={handleChange}
                placeholder="Unknown"
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Land Holding (Acres)</label>
              <input
                type="number"
                step="0.01"
                name="land_holding_acres"
                value={profile.land_holding_acres}
                onChange={handleChange}
                placeholder="Unknown"
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 outline-none"
              />
            </div>
          </div>
        </div>

        {/* Section 4: Social & Special Categories */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
            <Users className="w-5 h-5 text-brand-600" />
            Social Category & Special Status
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Social Category</label>
              <select
                name="social_category"
                value={profile.social_category}
                onChange={handleChange}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 outline-none bg-white"
              >
                <option value="">Prefer not to say (Unknown)</option>
                <option value="General">General</option>
                <option value="OBC">OBC</option>
                <option value="SC">SC</option>
                <option value="ST">ST</option>
                <option value="EWS">EWS</option>
                <option value="prefer_not_to_say">Prefer Not to Say</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">BPL Ration Card Holder</label>
              <select
                name="bpl_card"
                value={profile.bpl_card}
                onChange={handleChange}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 outline-none bg-white"
              >
                <option value="">Prefer not to say (Unknown)</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Person with Disability</label>
              <select
                name="disability"
                value={profile.disability}
                onChange={handleChange}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 outline-none bg-white"
              >
                <option value="">Prefer not to say (Unknown)</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Minority Community</label>
              <select
                name="minority"
                value={profile.minority}
                onChange={handleChange}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 outline-none bg-white"
              >
                <option value="">Prefer not to say (Unknown)</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>
          </div>
        </div>

        {/* Submit Actions & Danger Zone */}
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4 pt-4 border-t border-slate-200">
          <button
            type="button"
            onClick={() => setShowDeleteModal(true)}
            className="text-xs font-semibold text-red-600 hover:text-red-700 hover:bg-red-50 px-3 py-2 rounded-lg border border-red-200 transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Delete Account & All Data
          </button>

          <button
            type="submit"
            disabled={saving}
            className="w-full sm:w-auto px-8 py-3 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-semibold text-sm rounded-xl shadow-md shadow-brand-600/20 flex items-center justify-center gap-2 transition-all cursor-pointer"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Profile Changes'}
          </button>
        </div>
      </form>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl border border-slate-200">
            <div className="flex items-center gap-3 text-red-600">
              <ShieldAlert className="w-8 h-8 shrink-0" />
              <h3 className="text-lg font-bold text-slate-900">Delete Account & Data</h3>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed">
              This action will permanently delete your account, saved profile attributes, recommendation history, and saved schemes. This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowDeleteModal(false)}
                className="px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 rounded-xl cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAccount}
                disabled={deleting}
                className="px-4 py-2 text-sm font-semibold text-white bg-red-600 hover:bg-red-700 rounded-xl cursor-pointer flex items-center gap-2"
              >
                {deleting ? 'Deleting...' : 'Permanently Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Profile;
