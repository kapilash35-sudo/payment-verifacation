import React from 'react';
import { ShieldCheck, TrendingUp, AlertTriangle } from 'lucide-react';

function Header({ payments, wsConnected }) {
  const total = payments.length;
  const approved = payments.filter(p => p.verification_status === 'APPROVED').length;
  const flagged = payments.filter(p => p.verification_status === 'NEEDS VERIFICATION').length;
  const saved = payments.filter(p => p.verification_status === 'REJECTED').reduce((acc, curr) => acc + (curr.extracted_amount || 0), 0);

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold text-gray-900 tracking-tight flex items-center gap-2">
          <ShieldCheck className="text-blue-600 h-8 w-8" />
          Automated Bank Payment Verification
        </h1>
        <div className="flex items-center gap-2">
          <div className={`text-sm px-3 py-1 rounded-full font-medium flex items-center gap-1.5 ${
            wsConnected ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'
          }`}>
            <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
            {wsConnected ? 'Live Updates Active' : 'Connecting...'}
          </div>
        </div>
      </div>
      
      <div className="grid grid-cols-4 gap-4">
        <StatCard title="Total Processed" value={total} type="neutral" />
        <StatCard title="Approved %" value={total ? Math.round((approved/total)*100) + '%' : '0%'} type="success" />
        <StatCard title="Flagged for Audit" value={flagged} type="warning" icon={<AlertTriangle className="h-4 w-4 text-yellow-600" />} />
        <StatCard title="Fraud Prevented" value={`LKR ${saved.toLocaleString()}`} type="danger" icon={<TrendingUp className="h-4 w-4 text-red-600" />} />
      </div>
    </header>
  );
}

function StatCard({ title, value, type, icon }) {
  const colorMap = {
    neutral: 'bg-gray-50 text-gray-900 border-gray-100',
    success: 'bg-green-50 text-green-700 border-green-100',
    warning: 'bg-yellow-50 text-yellow-700 border-yellow-100',
    danger: 'bg-red-50 text-red-700 border-red-100'
  };

  return (
    <div className={`p-4 rounded-xl border ${colorMap[type]} flex flex-col`}>
      <span className="text-xs font-semibold uppercase tracking-wider opacity-75 flex items-center gap-1">
        {icon} {title}
      </span>
      <span className="text-2xl font-bold mt-1">{value}</span>
    </div>
  );
}

export default Header;
