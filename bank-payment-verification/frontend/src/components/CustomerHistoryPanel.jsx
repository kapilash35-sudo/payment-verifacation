import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { User, Shield, AlertTriangle, Loader2 } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api/v1';

const RISK_COLORS = {
  LOW: 'bg-green-100 text-green-800 border-green-200',
  MEDIUM: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  HIGH: 'bg-orange-100 text-orange-800 border-orange-200',
  BLACKLISTED: 'bg-red-100 text-red-800 border-red-200',
};

const STATUS_COLORS = {
  APPROVED: 'bg-green-100 text-green-700',
  REJECTED: 'bg-red-100 text-red-700',
  'NEEDS VERIFICATION': 'bg-yellow-100 text-yellow-700',
};

function CustomerHistoryPanel({ customerName }) {
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!customerName) {
      setHistory(null);
      return;
    }
    setLoading(true);
    axios
      .get(`${API_BASE}/customers/${encodeURIComponent(customerName)}/history`)
      .then((res) => setHistory(res.data))
      .catch((err) => console.error('Failed to fetch customer history:', err))
      .finally(() => setLoading(false));
  }, [customerName]);

  if (!customerName) return null;

  const profile = history?.risk_profile;

  return (
    <div className="border-t border-gray-200 bg-gray-50 flex flex-col max-h-72">
      <div className="p-3 border-b border-gray-100 font-semibold text-gray-700 text-sm flex items-center gap-2 sticky top-0 bg-gray-50">
        <User size={16} />
        Customer History
      </div>

      {loading ? (
        <div className="flex justify-center p-4">
          <Loader2 className="animate-spin text-blue-500" size={20} />
        </div>
      ) : (
        <div className="overflow-y-auto flex-1 p-3 space-y-3">
          {profile && (
            <div className={`p-3 rounded-lg border text-sm ${RISK_COLORS[profile.risk_level] || RISK_COLORS.LOW}`}>
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold flex items-center gap-1">
                  <Shield size={14} />
                  {customerName}
                </span>
                <span className="text-xs font-bold uppercase px-2 py-0.5 rounded-full bg-white/60">
                  {profile.risk_level}
                </span>
              </div>
              <div className="text-xs opacity-80 space-y-0.5">
                <p>Risk Score: {(profile.risk_score * 100).toFixed(0)}%</p>
                <p>
                  {profile.total_submissions} submissions · {profile.approved_count} approved ·{' '}
                  {profile.rejected_count} rejected
                </p>
                {profile.risk_level === 'HIGH' || profile.risk_level === 'BLACKLISTED' ? (
                  <p className="flex items-center gap-1 font-medium mt-1">
                    <AlertTriangle size={12} /> High-risk customer — extra scrutiny applied
                  </p>
                ) : null}
              </div>
            </div>
          )}

          {history?.payments?.length > 0 ? (
            <div className="space-y-1">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Past Submissions</p>
              {history.payments.map((p) => (
                <div
                  key={p.id}
                  className="flex justify-between items-center text-xs bg-white rounded-lg px-3 py-2 border border-gray-100"
                >
                  <div>
                    <span className="font-medium text-gray-800">{p.order_id}</span>
                    <span className="text-gray-400 ml-2">
                      {new Date(p.processed_at).toLocaleDateString()}
                    </span>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full font-medium ${
                      STATUS_COLORS[p.verification_status] || 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {p.verification_status}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            !profile && <p className="text-xs text-gray-400 text-center py-2">No history found</p>
          )}
        </div>
      )}
    </div>
  );
}

export default CustomerHistoryPanel;
