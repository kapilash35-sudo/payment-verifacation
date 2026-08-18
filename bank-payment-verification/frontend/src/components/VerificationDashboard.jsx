import React from 'react';
import { CheckCircle, XCircle, AlertCircle, MessageSquare } from 'lucide-react';

function VerificationDashboard({ payment, onAction }) {
  const isApproved = payment.verification_status === 'APPROVED';
  const isRejected = payment.verification_status === 'REJECTED';
  const isPending = payment.verification_status === 'NEEDS VERIFICATION';

  const badgeColor = isApproved ? 'bg-green-100 text-green-800 border-green-200' :
                     isRejected ? 'bg-red-100 text-red-800 border-red-200' :
                     'bg-yellow-100 text-yellow-800 border-yellow-200';

  const Icon = isApproved ? CheckCircle : isRejected ? XCircle : AlertCircle;

  return (
    <div className="flex flex-col h-full space-y-6">
      {/* Header Status */}
      <div className={`p-4 rounded-xl border flex items-center gap-4 ${badgeColor}`}>
        <Icon size={32} className={isApproved ? 'text-green-600' : isRejected ? 'text-red-600' : 'text-yellow-600'} />
        <div>
          <h2 className="text-xl font-bold capitalize">{payment.verification_status}</h2>
          <p className="text-sm opacity-80">Confidence Score: {(payment.confidence_score * 100).toFixed(0)}%</p>
        </div>
      </div>

      {/* Fraud Flags / Reasons */}
      {payment.decision_reasons && Object.keys(payment.decision_reasons).length > 0 && (
        <div className="bg-red-50 border border-red-100 rounded-xl p-4">
          <h3 className="text-sm font-bold text-red-900 mb-2 uppercase tracking-wide flex items-center gap-2">
            <AlertCircle size={16} /> Decision Reasons
          </h3>
          <ul className="list-disc pl-5 text-sm text-red-800 space-y-1">
            {Object.entries(payment.decision_reasons).map(([key, val]) => (
              <li key={key}><strong>{key}:</strong> {val}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Comparison Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-sm text-left">
          <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr>
              <th className="px-4 py-3">Field</th>
              <th className="px-4 py-3">Expected (Order)</th>
              <th className="px-4 py-3">Extracted (Slip)</th>
              <th className="px-4 py-3 text-center">Match</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            <ComparisonRow 
              label="Amount" 
              expected={`LKR ${payment.order?.expected_amount?.toLocaleString() || 'N/A'}`} 
              extracted={`LKR ${payment.extracted_amount?.toLocaleString() || 'N/A'}`} 
              match={payment.order?.expected_amount === payment.extracted_amount}
            />
            <ComparisonRow 
              label="Reference ID" 
              expected="Any" 
              extracted={payment.extracted_ref_id || 'Not Found'} 
              match={!!payment.extracted_ref_id}
            />
          </tbody>
        </table>
      </div>

      {/* SMS Evidence */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
        <h3 className="text-sm font-bold text-blue-900 mb-2 uppercase tracking-wide flex items-center gap-2">
          <MessageSquare size={16} /> Bank SMS Evidence
        </h3>
        {payment.decision_reasons?.SMS === "Matched with Bank SMS" ? (
          <p className="text-sm text-blue-800">✅ A matching SMS was found for this transaction.</p>
        ) : (
          <p className="text-sm text-blue-800 opacity-70">No matching SMS found yet.</p>
        )}
      </div>

      <div className="flex-grow"></div>

      {/* Action Buttons */}
      <div className="flex gap-4 pt-4 border-t border-gray-100">
        <button 
          onClick={() => onAction(payment.id, 'APPROVED', 'Manual review: Approved by Admin')}
          className="flex-1 bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg font-medium shadow transition-colors"
        >
          Force Approve
        </button>
        <button 
          onClick={() => onAction(payment.id, 'REJECTED', 'Manual review: Rejected by Admin')}
          className="flex-1 bg-red-600 hover:bg-red-700 text-white py-3 rounded-lg font-medium shadow transition-colors"
        >
          Reject (Fraud)
        </button>
        <button 
          onClick={() => onAction(payment.id, 'NEEDS VERIFICATION', 'Manual review: Requested new slip from customer')}
          className="flex-1 bg-yellow-500 hover:bg-yellow-600 text-white py-3 rounded-lg font-medium shadow transition-colors"
        >
          Request New Slip
        </button>
        <button 
          onClick={() => alert(`Message to customer: ${payment.customer_reply}`)}
          className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-800 py-3 rounded-lg font-medium shadow-sm transition-colors border border-gray-300"
        >
          View Reply
        </button>
      </div>
    </div>
  );
}

function ComparisonRow({ label, expected, extracted, match }) {
  return (
    <tr className="bg-white hover:bg-gray-50">
      <td className="px-4 py-3 font-medium text-gray-900">{label}</td>
      <td className="px-4 py-3 text-gray-600">{expected}</td>
      <td className="px-4 py-3 text-gray-900 font-semibold">{extracted}</td>
      <td className="px-4 py-3 text-center">
        {match ? <CheckCircle className="text-green-500 mx-auto" size={18}/> : <XCircle className="text-red-500 mx-auto" size={18}/>}
      </td>
    </tr>
  );
}

export default VerificationDashboard;
