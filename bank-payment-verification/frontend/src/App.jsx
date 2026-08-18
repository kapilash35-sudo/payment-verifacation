import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import Header from './components/Header';
import ImageViewer from './components/ImageViewer';
import VerificationDashboard from './components/VerificationDashboard';
import CustomerHistoryPanel from './components/CustomerHistoryPanel';
import { Loader2, Bell, X } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api/v1';
const WS_URL = 'ws://localhost:8000/ws';

function playNotificationSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.12, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.3);
  } catch {
    // Audio not available
  }
}

function App() {
  const [payments, setPayments] = useState([]);
  const [selectedPayment, setSelectedPayment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const [toast, setToast] = useState(null);
  const [newPaymentIds, setNewPaymentIds] = useState(new Set());
  const selectedPaymentRef = useRef(selectedPayment);

  useEffect(() => {
    selectedPaymentRef.current = selectedPayment;
  }, [selectedPayment]);

  const fetchPayments = useCallback(async (selectLatest = false) => {
    try {
      setLoading(true);
      const res = await axios.get(`${API_BASE}/payments`);
      setPayments(res.data);
      if (selectLatest && res.data.length > 0) {
        setSelectedPayment(res.data[0]);
      } else if (res.data.length > 0 && !selectedPaymentRef.current) {
        setSelectedPayment(res.data[0]);
      } else if (selectedPaymentRef.current) {
        const updated = res.data.find((p) => p.id === selectedPaymentRef.current.id);
        if (updated) setSelectedPayment(updated);
      }
    } catch (err) {
      console.error('Failed to fetch payments:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPayments();
  }, [fetchPayments]);

  useEffect(() => {
    let ws;
    let reconnectTimer;

    const connect = () => {
      ws = new WebSocket(WS_URL);

      ws.onopen = () => setWsConnected(true);

      ws.onclose = () => {
        setWsConnected(false);
        reconnectTimer = setTimeout(connect, 3000);
      };

      ws.onerror = () => ws.close();

      ws.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'pong') return;

        if (data.type === 'new_payment') {
          playNotificationSound();
          setToast({
            message: '🔔 New Payment Received!',
            detail: `${data.customer_name} · Order ${data.order_id}`,
          });
          setTimeout(() => setToast(null), 5000);

          setNewPaymentIds((prev) => new Set([...prev, data.payment_id]));
          setTimeout(() => {
            setNewPaymentIds((prev) => {
              const next = new Set(prev);
              next.delete(data.payment_id);
              return next;
            });
          }, 3000);

          await fetchPayments(true);
        } else if (data.type === 'status_changed') {
          setPayments((prev) =>
            prev.map((p) =>
              p.id === data.payment_id ? { ...p, verification_status: data.new_status } : p
            )
          );
          setSelectedPayment((prev) =>
            prev?.id === data.payment_id ? { ...prev, verification_status: data.new_status } : prev
          );
        }
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, [fetchPayments]);

  const handleAction = async (paymentId, action, reason) => {
    try {
      await axios.post(`${API_BASE}/payments/${paymentId}/manual-override`, {
        action,
        reason,
      });
      await fetchPayments();
    } catch (err) {
      console.error('Failed to update status', err);
      alert('Failed to update status');
    }
  };

  const customerName = selectedPayment?.order?.customer_name;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-sans text-gray-900">
      <Header payments={payments} wsConnected={wsConnected} />

      {toast && (
        <div className="fixed top-4 right-4 z-50 animate-slide-in">
          <div className="bg-blue-600 text-white px-4 py-3 rounded-xl shadow-lg flex items-center gap-3 min-w-64">
            <Bell size={20} className="shrink-0" />
            <div className="flex-1">
              <p className="font-semibold text-sm">{toast.message}</p>
              {toast.detail && <p className="text-xs opacity-80">{toast.detail}</p>}
            </div>
            <button onClick={() => setToast(null)} className="opacity-70 hover:opacity-100">
              <X size={16} />
            </button>
          </div>
        </div>
      )}

      <main className="flex-1 flex overflow-hidden p-6 gap-6">
        <aside className="w-1/4 bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden flex flex-col">
          <div className="p-4 border-b border-gray-100 font-semibold text-gray-700 bg-gray-50">
            Recent Submissions
          </div>
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex justify-center p-8">
                <Loader2 className="animate-spin text-blue-500" />
              </div>
            ) : (
              <div className="flex flex-col">
                {payments.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setSelectedPayment(p)}
                    className={`p-4 border-b border-gray-50 text-left hover:bg-gray-50 transition-colors ${
                      newPaymentIds.has(p.id) ? 'animate-slide-in bg-blue-50/80' : ''
                    } ${
                      selectedPayment?.id === p.id
                        ? 'bg-blue-50 border-l-4 border-l-blue-500'
                        : 'border-l-4 border-l-transparent'
                    }`}
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-medium text-sm">Order: {p.order_id}</span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          p.verification_status === 'APPROVED'
                            ? 'bg-green-100 text-green-700'
                            : p.verification_status === 'REJECTED'
                              ? 'bg-red-100 text-red-700'
                              : 'bg-yellow-100 text-yellow-700'
                        }`}
                      >
                        {p.verification_status}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500">
                      {p.order?.customer_name && (
                        <span className="mr-2">{p.order.customer_name}</span>
                      )}
                      {new Date(p.processed_at).toLocaleString()}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <CustomerHistoryPanel customerName={customerName} />
        </aside>

        <div className="flex-1 flex gap-6 bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          {selectedPayment ? (
            <>
              <div className="w-1/2 border-r border-gray-100 bg-gray-50 flex flex-col p-4 relative">
                <ImageViewer
                  imagePath={selectedPayment.image_path}
                  elaImagePath={selectedPayment.ela_image_path}
                  elaScore={selectedPayment.ela_score}
                  ocrBoxes={selectedPayment.ocr_boxes}
                />
              </div>

              <div className="w-1/2 p-6 overflow-y-auto">
                <VerificationDashboard payment={selectedPayment} onAction={handleAction} />
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-400">
              Select a payment to view details
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
