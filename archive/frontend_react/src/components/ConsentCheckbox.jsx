import React from 'react';
import { ShieldCheck } from 'lucide-react';

const ConsentCheckbox = ({ checked, onChange, required = true, error }) => {
  return (
    <div className="space-y-2">
      <div className="flex items-start gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
        <input
          id="data-consent"
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          required={required}
          className="mt-1 h-4 w-4 text-brand-600 rounded border-slate-300 focus:ring-brand-500 cursor-pointer"
        />
        <label htmlFor="data-consent" className="text-sm text-slate-600 leading-relaxed cursor-pointer select-none">
          <span className="font-semibold text-slate-800 flex items-center gap-1.5 mb-0.5">
            <ShieldCheck className="w-4 h-4 text-brand-600 inline" />
            Data Protection & Privacy Consent
          </span>
          I consent to the secure storage and deterministic eligibility evaluation of my demographic profile. My data will be used strictly to match eligible Central and Maharashtra government schemes and will never be shared without authorization.
        </label>
      </div>
      {error && <p className="text-xs text-red-600 font-medium">{error}</p>}
    </div>
  );
};

export default ConsentCheckbox;
