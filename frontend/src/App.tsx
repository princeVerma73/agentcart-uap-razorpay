import React, { useState, useEffect, useRef } from 'react';
import { 
  Bot, ShieldCheck, ShoppingCart, Zap, AlertTriangle, CheckCircle, 
  Terminal, Lock, RefreshCw, ArrowRight, DollarSign, Database, 
  Play, FileText, Check, X, Layers, Activity, Sparkles
} from 'lucide-react';

interface Product {
  id: string;
  name: string;
  category: string;
  description: string;
  price: number;
  stock: number;
  specs: Record<string, any>;
  rating: number;
  merchant_name: string;
}

interface AgentStep {
  step_number: number;
  title: string;
  thought: string;
  action: string;
  status: string;
  data?: any;
}

interface AuditLog {
  id: string;
  session_id: string;
  timestamp: string;
  event_type: string;
  status: string;
  summary: string;
  details: Record<string, any>;
  cryptographic_hash: string;
}

interface PolicyConfig {
  max_single_transaction_limit: number;
  auto_approve_limit: number;
  allowed_categories: string[];
  require_human_approval_always: boolean;
  enforce_stock_check: boolean;
}

interface GrowthMetrics {
  total_sessions: number;
  recommendation_opportunities: number;
  purchases: number;
  conversion_rate: number;
  total_revenue: number;
  average_order_value: number;
  upsell_opportunities: number;
  upsell_accepted: number;
  upsell_rejected: number;
  upsell_acceptance_rate: number;
  cross_sell_opportunities: number;
  cross_sell_accepted: number;
  cross_sell_rejected: number;
  cross_sell_acceptance_rate: number;
  incremental_revenue: number;
  revenue_per_session: number;
}

interface MerchantAnalytics {
  gmv: number;
  incremental_revenue: number;
  purchases: number;
  average_order_value: number;
  pre_authorized_transactions: number;
  hitl_approved_transactions: number;
  hitl_gate_ratio: number;
  failure_recoveries: number;
}

interface RazorpayCheckoutResponse {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

interface RazorpayCheckoutOptions {
  key: string;
  amount: number;
  currency: string;
  order_id: string;
  name: string;
  description: string;
  handler: (response: RazorpayCheckoutResponse) => void;
  modal?: { ondismiss: () => void };
}

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayCheckoutOptions) => { open: () => void };
  }
}

const loadRazorpayCheckout = () => new Promise<void>((resolve, reject) => {
  if (window.Razorpay) {
    resolve();
    return;
  }

  const script = document.createElement('script');
  script.src = 'https://checkout.razorpay.com/v1/checkout.js';
  script.onload = () => resolve();
  script.onerror = () => reject(new Error('Unable to load Razorpay Checkout.'));
  document.body.appendChild(script);
});

export default function App() {
  // State
  const [products, setProducts] = useState<Product[]>([]);
  const [promptGoal, setPromptGoal] = useState<string>("Buy 2 braided 4K HDMI cables for office setup");
  const [maxBudget, setMaxBudget] = useState<number>(3000);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [metrics, setMetrics] = useState<GrowthMetrics | null>(null);
  const [merchantAnalytics, setMerchantAnalytics] = useState<MerchantAnalytics | null>(null);
  const [lastCheckout, setLastCheckout] = useState<{sessionId: string; orderId: string} | null>(null);
  const [policy, setPolicy] = useState<PolicyConfig>({
    max_single_transaction_limit: 10000,
    auto_approve_limit: 3000,
    allowed_categories: ["accessories", "cables", "peripherals", "pantry"],
    require_human_approval_always: false,
    enforce_stock_check: true
  });

  // Pending HITL State
  const [pendingHitl, setPendingHitl] = useState<{
    sessionId: string;
    proposal: any;
    verifiedTotal: number;
    hitlToken: string;
  } | null>(null);

  const logsEndRef = useRef<HTMLDivElement>(null);

  // Fetch initial catalog, policy, audit logs, and metrics
  useEffect(() => {
    fetchCatalog();
    fetchPolicy();
    fetchAuditLogs();
    fetchMetrics();
    fetchMerchantAnalytics();
    const interval = setInterval(() => {
      fetchAuditLogs();
      fetchMetrics();
      fetchMerchantAnalytics();
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [steps]);

  const fetchMetrics = async () => {
    try {
      const res = await fetch('/api/growth/metrics');
      const data = await res.json();
      setMetrics(data);
    } catch (e) {
      console.error("Failed to fetch metrics", e);
    }
  };

  const fetchMerchantAnalytics = async () => {
    try {
      const res = await fetch('/api/merchant/analytics');
      setMerchantAnalytics(await res.json());
    } catch (e) {
      console.error("Failed to fetch merchant analytics", e);
    }
  };

  const handleGrowthInteract = async (offerType: string, action: string, productId: string, baseProductId: string, quantity: number) => {
    try {
      await fetch('/api/growth/interact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: activeSessionId || 'sess_ui_interact',
          offer_type: offerType,
          action: action,
          product_id: productId,
          base_product_id: baseProductId,
          quantity
        })
      });
      fetchMetrics();
      fetchAuditLogs();
    } catch (e) {
      console.error("Failed growth interaction", e);
    }
  };


  const fetchCatalog = async () => {
    try {
      const res = await fetch('/api/catalog');
      const data = await res.json();
      setProducts(data.products || []);
    } catch (e) {
      console.error("Failed to fetch catalog", e);
    }
  };

  const fetchPolicy = async () => {
    try {
      const res = await fetch('/api/policy');
      const data = await res.json();
      setPolicy(data);
    } catch (e) {
      console.error("Failed to fetch policy", e);
    }
  };

  const fetchAuditLogs = async () => {
    try {
      const res = await fetch('/api/audit-logs');
      const data = await res.json();
      setAuditLogs(data.logs || []);
    } catch (e) {
      console.error("Failed to fetch logs", e);
    }
  };

  const updatePolicyConfig = async (newPolicy: PolicyConfig) => {
    setPolicy(newPolicy);
    try {
      await fetch('/api/policy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newPolicy)
      });
    } catch (e) {
      console.error("Failed to update policy", e);
    }
  };

  // Run Agent
  const handleRunAgent = async (customGoal?: string, customBudget?: number) => {
    const goalToRun = customGoal || promptGoal;
    const budgetToRun = customBudget !== undefined ? customBudget : maxBudget;
    
    setIsRunning(true);
    setSteps([]);
    setPendingHitl(null);
    const newSessionId = `sess_${Math.random().toString(36).substring(2, 10)}`;
    setActiveSessionId(newSessionId);

    try {
      const response = await fetch('/api/agent/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          goal: goalToRun,
          session_id: newSessionId,
          max_budget: budgetToRun
        })
      });

      if (!response.body) return;

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.replace("data: ", "").trim();
            if (dataStr === "[DONE]") {
              setIsRunning(false);
              fetchAuditLogs();
              fetchCatalog();
              break;
            }

            try {
              const step: AgentStep = JSON.parse(dataStr);
              setSteps(prev => [...prev, step]);

              if (step.status === "PENDING_APPROVAL" && step.data?.verification) {
                setPendingHitl({
                  sessionId: newSessionId,
                  proposal: step.data.proposal,
                  verifiedTotal: step.data.verification.verified_total,
                  hitlToken: step.data.hitl_token || step.data.verification.hitl_token || ""
                });
                setIsRunning(false);
              }

              if (step.status === 'PENDING_PAYMENT' && step.data?.checkout && step.data?.order) {
                setLastCheckout({ sessionId: newSessionId, orderId: step.data.order.id });
                void openRazorpayCheckout(step.data.checkout, newSessionId, step.data.order);
              }
            } catch (err) {
              console.error("Parse error on step", err);
            }
          }
        }
      }
    } catch (e) {
      console.error("Agent execution failed", e);
    } finally {
      setIsRunning(false);
      fetchAuditLogs();
      fetchCatalog();
    }
  };

  const recordCheckoutFailure = async (sessionId: string, orderId: string, reason: 'cancelled' | 'failed') => {
    await fetch('/api/payments/checkout-failed', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, razorpay_order_id: orderId, reason })
    });
    fetchAuditLogs();
  };

  const openRazorpayCheckout = async (checkoutOptions: Omit<RazorpayCheckoutOptions, 'handler' | 'modal'>, sessionId: string, order: any) => {
    try {
      setLastCheckout({ sessionId, orderId: order.id });
      await loadRazorpayCheckout();
      if (!window.Razorpay) throw new Error('Razorpay Checkout did not initialize.');

      let paymentCompleted = false;
      let paymentSubmissionStarted = false;
      const checkout = new window.Razorpay({
        ...checkoutOptions,
        handler: async (payment) => {
          paymentSubmissionStarted = true;
          try {
            const verificationResponse = await fetch('/api/payments/verify', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ session_id: sessionId, ...payment })
            });
            const verification = await verificationResponse.json();
            if (!verificationResponse.ok) throw new Error(verification.detail || 'Payment verification failed.');

            paymentCompleted = true;
            setSteps(prev => [...prev, {
              step_number: prev.length + 1,
              title: 'Razorpay Payment Verified',
              thought: `Razorpay payment ${payment.razorpay_payment_id} was verified server-side.`,
              action: 'razorpay_payment_verified',
              status: 'SUCCESS',
              data: { order, settlement: payment }
            }]);
            setPendingHitl(null);
            fetchAuditLogs();
            fetchMetrics();
          } catch (error) {
            console.error('Payment verification failed', error);
            await recordCheckoutFailure(sessionId, order.id, 'failed');
          }
        },
        modal: {
          ondismiss: () => {
            if (!paymentCompleted && !paymentSubmissionStarted) void recordCheckoutFailure(sessionId, order.id, 'cancelled');
          }
        }
      });
      checkout.open();
    } catch (error) {
      await recordCheckoutFailure(sessionId, order.id, 'failed');
      throw error;
    }
  };

  const handleApproveHitl = async () => {
    if (!pendingHitl) return;
    try {
      const res = await fetch('/api/agent/approve-hitl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: pendingHitl.sessionId,
          proposal: pendingHitl.proposal,
          verified_total: pendingHitl.verifiedTotal,
          hitl_token: pendingHitl.hitlToken
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Unable to create Razorpay order.');

      if (data.status === 'PENDING_PAYMENT') {
        await openRazorpayCheckout(data.checkout, pendingHitl.sessionId, data.order);
        return;
      }

      setSteps(prev => [
        ...prev,
        {
          step_number: prev.length + 1,
          title: "Human Approval Received & Settled",
          thought: `Cryptographic sign-off verified. Razorpay Order ${data.order.id} settled autonomously for ₹${pendingHitl.verifiedTotal.toLocaleString('en-IN')}.`,
          action: "hitl_approved_and_settled",
          status: "SUCCESS",
          data: data
        }
      ]);
      setPendingHitl(null);
      fetchAuditLogs();
    } catch (e) {
      console.error("Failed to approve HITL", e);
    }
  };

  // Chaos Simulators
  const triggerPriceSurge = async (productId: string, currentPrice: number) => {
    const surgePrice = Math.round(currentPrice * 1.8);
    await fetch('/api/catalog/simulate-price-surge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: productId, new_price: surgePrice })
    });
    fetchCatalog();
  };

  const triggerStockout = async (productId: string) => {
    await fetch('/api/catalog/simulate-stockout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: productId })
    });
    fetchCatalog();
  };

  const simulatePaymentFailure = async () => {
    if (!lastCheckout) {
      setSteps(prev => [...prev, {
        step_number: prev.length + 1,
        title: 'Payment Failure Demo Ready',
        thought: 'Start a checkout first. AgentCart will never show a paid state without server-side Razorpay verification.',
        action: 'payment_failure_demo', status: 'INFO'
      }]);
      return;
    }
    await recordCheckoutFailure(lastCheckout.sessionId, lastCheckout.orderId, 'failed');
    setSteps(prev => [...prev, {
      step_number: prev.length + 1,
      title: 'Payment Gateway Failure Safely Recorded',
      thought: `Order ${lastCheckout.orderId} remains failed; no settlement or revenue was recorded.`,
      action: 'payment_failure_simulated', status: 'REJECTED'
    }]);
    setLastCheckout(null);
    fetchMerchantAnalytics();
  };

  const resetCatalog = async () => {
    await fetch('/api/catalog/reset', { method: 'POST' });
    fetchCatalog();
  };

  return (
    <div className="min-h-screen bg-[#070c18] text-slate-100 flex flex-col">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-[#0c1427]/80 backdrop-blur-md sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between shadow-lg">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-blue-500/20 shadow-md">
            <Bot className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-bold text-lg tracking-tight text-white">AgentCart</h1>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
                Track 01: Agentic Commerce
              </span>
            </div>
            <p className="text-xs text-slate-400">Autonomous Buyer &amp; Merchant Protocol on Razorpay Rails</p>
          </div>
        </div>

        {/* Status Indicators */}
        <div className="flex items-center space-x-3 text-xs">
          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>Razorpay Rails: Ready</span>
          </div>
          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>Policy Gate: Active</span>
          </div>
          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-400">
            <Lock className="h-3.5 w-3.5" />
            <span>UAP / AP2 Compliant</span>
          </div>
        </div>
      </header>

      {/* Main Grid: 3 Columns */}
      <main className="flex-1 p-6 grid grid-cols-12 gap-6 overflow-hidden max-w-[1700px] w-full mx-auto">
        
        {/* Left Column: AI Buyer Agent Command Center (Cols: 4) */}
        <section className="col-span-12 lg:col-span-4 flex flex-col space-y-4">
          <div className="bg-[#0f192e] border border-slate-800 rounded-xl p-4 shadow-md">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider flex items-center gap-1.5">
                <Bot className="h-4 w-4" /> Agent Goal Delegation
              </span>
              <span className="text-[11px] text-slate-400">Natural Language Intent</span>
            </div>

            {/* Prompt Input */}
            <div className="space-y-3">
              <textarea
                value={promptGoal}
                onChange={(e) => setPromptGoal(e.target.value)}
                placeholder="e.g. Order 2 braided 4K HDMI cables under ₹2,000..."
                rows={3}
                className="w-full bg-[#080d1a] border border-slate-700/80 rounded-lg p-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors resize-none font-sans"
              />

              <div className="flex items-center justify-between text-xs text-slate-400">
                <label className="flex items-center space-x-1.5">
                  <span>User Budget Cap:</span>
                  <span className="font-semibold text-slate-200">₹{maxBudget.toLocaleString('en-IN')}</span>
                </label>
                <input
                  type="range"
                  min={1000}
                  max={20000}
                  step={500}
                  value={maxBudget}
                  onChange={(e) => setMaxBudget(Number(e.target.value))}
                  className="w-32 accent-blue-500 cursor-pointer"
                />
              </div>

              {/* Action Button */}
              <button
                onClick={() => handleRunAgent()}
                disabled={isRunning || !promptGoal.trim()}
                className="w-full py-2.5 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white font-medium rounded-lg text-sm flex items-center justify-center space-x-2 shadow-lg shadow-blue-500/20 transition-all cursor-pointer"
              >
                {isRunning ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    <span>Agent Transacting...</span>
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 fill-white" />
                    <span>Execute Autonomous Purchase</span>
                  </>
                )}
              </button>
            </div>

            {/* Demonstration Presets */}
            <div className="mt-4 pt-3 border-t border-slate-800/80">
              <p className="text-[11px] font-medium text-slate-400 mb-2">Evaluation &amp; Demo Scenarios:</p>
              <div className="grid grid-cols-2 gap-1.5 text-xs">
                <button
                  onClick={() => {
                    const g = "Buy 2 braided 4K HDMI cables for office setup";
                    setPromptGoal(g);
                    setMaxBudget(3000);
                    handleRunAgent(g, 3000);
                  }}
                  className="text-left p-2 rounded bg-slate-800/60 hover:bg-slate-800 border border-slate-700/50 text-slate-300 transition-colors"
                >
                  <span className="font-medium text-emerald-400 block mb-0.5">Scenario 1: Pre-Auth</span>
                  <span className="text-[11px] text-slate-400">Auto-approved under limit</span>
                </button>

                <button
                  onClick={() => {
                    const g = "Purchase 1 Keychron K2 mechanical keyboard";
                    setPromptGoal(g);
                    setMaxBudget(8000);
                    handleRunAgent(g, 8000);
                  }}
                  className="text-left p-2 rounded bg-slate-800/60 hover:bg-slate-800 border border-slate-700/50 text-slate-300 transition-colors"
                >
                  <span className="font-medium text-amber-400 block mb-0.5">Scenario 2: HITL Gate</span>
                  <span className="text-[11px] text-slate-400">High-value sign-off</span>
                </button>

                <button
                  onClick={() => {
                    const g = "Restock 2kg dark roast coffee beans for pantry";
                    setPromptGoal(g);
                    setMaxBudget(5000);
                    handleRunAgent(g, 5000);
                  }}
                  className="text-left p-2 rounded bg-slate-800/60 hover:bg-slate-800 border border-slate-700/50 text-slate-300 transition-colors"
                >
                  <span className="font-medium text-blue-400 block mb-0.5">Scenario 3: B2B Pantry</span>
                  <span className="text-[11px] text-slate-400">Multi-unit purchase</span>
                </button>

                <button
                  onClick={() => {
                    const g = "Order 2 Logitech MX Master 3S mice";
                    setPromptGoal(g);
                    setMaxBudget(15000);
                    handleRunAgent(g, 15000);
                  }}
                  className="text-left p-2 rounded bg-slate-800/60 hover:bg-slate-800 border border-slate-700/50 text-slate-300 transition-colors"
                >
                  <span className="font-medium text-rose-400 block mb-0.5">Scenario 4: Hard Block</span>
                  <span className="text-[11px] text-slate-400">Exceeds ceiling (₹10k)</span>
                </button>
              </div>
            </div>
          </div>

          {/* Live Agent Execution Stream */}
          <div className="flex-1 bg-[#0f192e] border border-slate-800 rounded-xl p-4 flex flex-col overflow-hidden shadow-md">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Terminal className="h-4 w-4 text-blue-400" /> Live Agent Reasoning Trace
              </span>
              {activeSessionId && (
                <span className="font-mono text-[10px] text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                  {activeSessionId}
                </span>
              )}
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pt-3 pr-1 text-xs">
              {steps.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 text-center py-12">
                  <Sparkles className="h-8 w-8 mb-2 opacity-30 text-blue-400" />
                  <p>Agent is idle.</p>
                  <p className="text-[11px]">Submit a purchase goal to watch autonomous tool execution.</p>
                </div>
              ) : (
                steps.map((step, idx) => (
                  <div 
                    key={idx} 
                    className={`p-3 rounded-lg border transition-all ${
                      step.status === 'SUCCESS' ? 'bg-emerald-950/20 border-emerald-500/30' :
                      step.status === 'REJECTED' ? 'bg-rose-950/20 border-rose-500/30' :
                      step.status === 'PENDING_APPROVAL' ? 'bg-amber-950/20 border-amber-500/30' :
                      step.status === 'RECOVERING' ? 'bg-purple-950/20 border-purple-500/30' :
                      'bg-slate-900/60 border-slate-800'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-[10px] text-slate-400">#{step.step_number}</span>
                        <span className="font-semibold text-slate-200">{step.title}</span>
                      </div>
                      <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${
                        step.status === 'SUCCESS' ? 'bg-emerald-500/20 text-emerald-400' :
                        step.status === 'REJECTED' ? 'bg-rose-500/20 text-rose-400' :
                        step.status === 'PENDING_APPROVAL' ? 'bg-amber-500/20 text-amber-400' :
                        step.status === 'RECOVERING' ? 'bg-purple-500/20 text-purple-400' :
                        'bg-blue-500/20 text-blue-400'
                      }`}>
                        {step.status}
                      </span>
                    </div>
                    <p className="text-slate-300 leading-relaxed font-sans">{step.thought}</p>
                    
                    {step.data?.upsell_candidate && (
                      <div className="mt-2.5 p-2.5 rounded bg-blue-950/30 border border-blue-500/40 text-[11px] space-y-1.5">
                        <div className="flex items-center justify-between text-blue-400 font-semibold">
                          <span className="flex items-center gap-1"><Sparkles className="h-3 w-3" /> Contextual Upsell Option</span>
                          <span>+₹{step.data.upsell_candidate.price_delta.toLocaleString('en-IN')}</span>
                        </div>
                        <p className="text-slate-300">{step.data.upsell_candidate.reason}</p>
                        <div className="flex items-center space-x-2 pt-1">
                          <button
                            onClick={() => handleGrowthInteract('upsell', 'accept', step.data.upsell_candidate.upsell_product.id, step.data.upsell_candidate.base_product_id, step.data.upsell_candidate.quantity)}
                            className="px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-[10px] font-semibold transition-colors cursor-pointer"
                          >
                            Accept Upgrade
                          </button>
                          <button
                            onClick={() => handleGrowthInteract('upsell', 'reject', step.data.upsell_candidate.upsell_product.id, step.data.upsell_candidate.base_product_id, step.data.upsell_candidate.quantity)}
                            className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded text-[10px] transition-colors cursor-pointer"
                          >
                            Decline
                          </button>
                        </div>
                      </div>
                    )}

                    {step.data?.cross_sell_candidate && (
                      <div className="mt-2.5 p-2.5 rounded bg-purple-950/30 border border-purple-500/40 text-[11px] space-y-1.5">
                        <div className="flex items-center justify-between text-purple-400 font-semibold">
                          <span className="flex items-center gap-1"><ShoppingCart className="h-3 w-3" /> Compatible Cross-Sell</span>
                          <span>+₹{step.data.cross_sell_candidate.additional_price.toLocaleString('en-IN')}</span>
                        </div>
                        <p className="text-slate-300">{step.data.cross_sell_candidate.reason}</p>
                        <div className="flex items-center space-x-2 pt-1">
                          <button
                            onClick={() => handleGrowthInteract('cross_sell', 'accept', step.data.cross_sell_candidate.cross_sell_product.id, step.data.cross_sell_candidate.base_product_id, step.data.cross_sell_candidate.quantity)}
                            className="px-2 py-1 bg-purple-600 hover:bg-purple-500 text-white rounded text-[10px] font-semibold transition-colors cursor-pointer"
                          >
                            Add to Cart
                          </button>
                          <button
                            onClick={() => handleGrowthInteract('cross_sell', 'reject', step.data.cross_sell_candidate.cross_sell_product.id, step.data.cross_sell_candidate.base_product_id, step.data.cross_sell_candidate.quantity)}
                            className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded text-[10px] transition-colors cursor-pointer"
                          >
                            Decline
                          </button>
                        </div>
                      </div>
                    )}

                    {step.data?.order && (
                      <div className="mt-2 p-2 rounded bg-slate-950/80 border border-slate-800 font-mono text-[11px] space-y-1">
                        <div className="text-emerald-400 font-medium flex items-center gap-1">
                          <CheckCircle className="h-3 w-3" /> Razorpay Order: {step.data.order.id}
                        </div>
                        <div className="text-slate-400">Amount: ₹{step.data.verified_total?.toLocaleString('en-IN')}</div>
                        <div className="text-slate-500 text-[10px]">Payment ID: {step.data.settlement?.razorpay_payment_id}</div>
                      </div>
                    )}

                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        </section>

        {/* Middle Column: Merchant Storefront & Chaos Simulator (Cols: 4) */}
        <section className="col-span-12 lg:col-span-4 flex flex-col space-y-4">
          <div className="bg-[#0f192e] border border-slate-800 rounded-xl p-4 flex flex-col h-full shadow-md">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
                <Database className="h-4 w-4" /> Merchant Inventory (MCP Catalog)
              </span>
              <button 
                onClick={resetCatalog}
                className="text-[11px] text-slate-400 hover:text-white flex items-center gap-1 bg-slate-800 px-2 py-1 rounded transition-colors"
              >
                <RefreshCw className="h-3 w-3" /> Reset Store
              </button>
            </div>

            <p className="text-xs text-slate-400 mb-3">
              Live inventory exposed via Model Context Protocol (MCP) to AI agents. Use simulation toggles to test fail-safes.
            </p>
            <button
              onClick={simulatePaymentFailure}
              className="mb-3 w-full py-2 rounded border border-rose-500/40 bg-rose-950/20 text-rose-300 text-xs font-semibold hover:bg-rose-950/40 transition-colors"
            >
              Simulate Payment Gateway Failure (no false confirmation)
            </button>

            {/* Product Cards */}
            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {products.map(p => (
                <div key={p.id} className="bg-[#080d1a] border border-slate-800/80 rounded-lg p-3 hover:border-slate-700 transition-all">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-200">{p.name}</h4>
                      <p className="text-xs text-slate-400 line-clamp-1 mt-0.5">{p.description}</p>
                    </div>
                    <span className="text-sm font-bold text-emerald-400 whitespace-nowrap ml-2">
                      ₹{p.price.toLocaleString('en-IN')}
                    </span>
                  </div>

                  <div className="flex items-center justify-between mt-2.5 text-xs text-slate-400">
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${
                        p.stock > 0 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20 font-bold'
                      }`}>
                        {p.stock > 0 ? `${p.stock} in stock` : 'OUT OF STOCK'}
                      </span>
                      <span className="text-[10px] text-slate-500">{p.merchant_name}</span>
                    </div>

                    {/* Chaos Action Buttons */}
                    <div className="flex items-center space-x-1.5">
                      <button
                        title="Simulate sudden price surge"
                        onClick={() => triggerPriceSurge(p.id, p.price)}
                        className="p-1 rounded bg-slate-800 hover:bg-amber-500/20 text-slate-400 hover:text-amber-400 text-[10px] border border-slate-700 transition-colors"
                      >
                        +Price Surge
                      </button>
                      <button
                        title="Simulate item stockout"
                        onClick={() => triggerStockout(p.id)}
                        className="p-1 rounded bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 text-[10px] border border-slate-700 transition-colors"
                      >
                        Deplete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Right Column: Financial Guardrails & Cryptographic Audit Ledger (Cols: 4) */}
        <section className="col-span-12 lg:col-span-4 flex flex-col space-y-4">
          
          {/* HITL Modal Drawer (If Pending) */}
          {pendingHitl && (
            <div className="bg-gradient-to-b from-amber-950/40 to-[#0f192e] border-2 border-amber-500/50 rounded-xl p-4 shadow-xl animate-bounce-short">
              <div className="flex items-center space-x-2 text-amber-400 mb-2">
                <AlertTriangle className="h-5 w-5" />
                <h3 className="font-bold text-sm">Human-in-the-Loop Sign-off Required</h3>
              </div>
              <p className="text-xs text-slate-300 mb-3">
                Transaction exceeds the autonomous pre-authorization ceiling of ₹{policy.auto_approve_limit.toLocaleString('en-IN')}. Please approve to execute on Razorpay.
              </p>

              <div className="bg-[#080d1a] rounded-lg p-2.5 mb-3 border border-slate-800 text-xs space-y-1">
                <div className="flex justify-between text-slate-400">
                  <span>Merchant:</span>
                  <span className="text-slate-200">CloudGear Technologies</span>
                </div>
                <div className="flex justify-between font-bold text-slate-100 text-sm pt-1 border-t border-slate-800">
                  <span>Verified Total:</span>
                  <span className="text-emerald-400">₹{pendingHitl.verifiedTotal.toLocaleString('en-IN')}</span>
                </div>
              </div>

              <div className="flex space-x-2">
                <button
                  onClick={handleApproveHitl}
                  className="flex-1 py-2 px-3 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg flex items-center justify-center space-x-1.5 shadow-md transition-colors cursor-pointer"
                >
                  <Check className="h-3.5 w-3.5" />
                  <span>Approve &amp; Settle Razorpay</span>
                </button>
                <button
                  onClick={() => setPendingHitl(null)}
                  className="py-2 px-3 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg transition-colors cursor-pointer"
                >
                  Reject
                </button>
              </div>
            </div>
          )}

          {/* Merchant Growth Engine Analytics Panel */}
          <div className="bg-[#0f192e] border border-slate-800 rounded-xl p-4 shadow-md">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                <Zap className="h-4 w-4" /> Merchant Growth Analytics
              </span>
              <span className="text-[10px] text-slate-400">Track 01 Metrics</span>
            </div>

            {!metrics || metrics.total_sessions === 0 ? (
              <p className="text-xs text-slate-500 text-center py-3">No evaluation data yet.</p>
            ) : (
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-[#080d1a] p-2 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-400">Sessions / Purchases</div>
                  <div className="font-bold text-slate-200 text-sm">{metrics.total_sessions} / {metrics.purchases}</div>
                </div>

                <div className="bg-[#080d1a] p-2 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-400">Conversion Rate</div>
                  <div className="font-bold text-emerald-400 text-sm">{metrics.conversion_rate}%</div>
                </div>

                <div className="bg-[#080d1a] p-2 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-400">Average Order Value</div>
                  <div className="font-bold text-slate-200 text-sm">₹{metrics.average_order_value.toLocaleString('en-IN')}</div>
                </div>

                <div className="bg-[#080d1a] p-2 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-400">Incremental Revenue</div>
                  <div className="font-bold text-amber-400 text-sm">₹{metrics.incremental_revenue.toLocaleString('en-IN')}</div>
                </div>

                <div className="bg-[#080d1a] p-2 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-400">Upsell Rate</div>
                  <div className="font-bold text-blue-400 text-sm">{metrics.upsell_acceptance_rate}%</div>
                </div>

                <div className="bg-[#080d1a] p-2 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-400">Cross-Sell Rate</div>
                  <div className="font-bold text-purple-400 text-sm">{metrics.cross_sell_acceptance_rate}%</div>
                </div>
              </div>
            )}
            {merchantAnalytics && (
              <div className="grid grid-cols-2 gap-2 text-xs mt-2 pt-2 border-t border-slate-800">
                <div className="bg-[#080d1a] p-2 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-400">Total Settled GMV</div>
                  <div className="font-bold text-emerald-400 text-sm">₹{merchantAnalytics.gmv.toLocaleString('en-IN')}</div>
                </div>
                <div className="bg-[#080d1a] p-2 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-400">Incremental Revenue</div>
                  <div className="font-bold text-amber-400 text-sm">₹{merchantAnalytics.incremental_revenue.toLocaleString('en-IN')}</div>
                </div>
                <div className="bg-[#080d1a] p-2 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-400">AOV / Settled Orders</div>
                  <div className="font-bold text-slate-200 text-sm">₹{merchantAnalytics.average_order_value.toLocaleString('en-IN')} ({merchantAnalytics.purchases || 0})</div>
                </div>
                <div className="bg-[#080d1a] p-2 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-400">HITL Gate Ratio</div>
                  <div className="font-bold text-blue-400 text-sm">{merchantAnalytics.hitl_gate_ratio}%</div>
                </div>
                <div className="bg-[#080d1a] p-2 rounded border border-slate-800 col-span-2 flex justify-between items-center">
                  <span className="text-[10px] text-slate-400">Stockout Auto-Recoveries:</span>
                  <span className="font-bold text-emerald-400 text-xs px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">{merchantAnalytics.failure_recoveries} Recovered</span>
                </div>
              </div>
            )}
          </div>

          {/* Policy Guardrails Config */}
          <div className="bg-[#0f192e] border border-slate-800 rounded-xl p-4 shadow-md">

            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4" /> Deterministic Policy Guardrails
              </span>
              <span className="text-[10px] text-slate-400">Security Gate</span>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <div className="flex justify-between text-slate-400 mb-1">
                  <span>Autonomous Pre-Auth Limit (UAP):</span>
                  <span className="font-semibold text-slate-200">₹{policy.auto_approve_limit.toLocaleString('en-IN')}</span>
                </div>
                <input
                  type="range"
                  min={500}
                  max={3000}
                  step={500}
                  value={policy.auto_approve_limit}
                  onChange={(e) => updatePolicyConfig({ ...policy, auto_approve_limit: Number(e.target.value) })}
                  className="w-full accent-emerald-500 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-slate-400 mb-1">
                  <span>Hard Spending Ceiling (Max Allowed):</span>
                  <span className="font-semibold text-slate-200">₹{policy.max_single_transaction_limit.toLocaleString('en-IN')}</span>
                </div>
                <input
                  type="range"
                  min={3000}
                  max={10000}
                  step={500}
                  value={policy.max_single_transaction_limit}
                  onChange={(e) => updatePolicyConfig({ ...policy, max_single_transaction_limit: Number(e.target.value) })}
                  className="w-full accent-emerald-500 cursor-pointer"
                />
              </div>

              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                <span>Always Require Human Approval</span>
                <input
                  type="checkbox"
                  checked={policy.require_human_approval_always}
                  onChange={(e) => updatePolicyConfig({ ...policy, require_human_approval_always: e.target.checked })}
                  className="accent-blue-500 cursor-pointer h-4 w-4"
                />
              </div>
            </div>
          </div>

          {/* Tamper-Evident Audit Ledger */}
          <div className="flex-1 bg-[#0f192e] border border-slate-800 rounded-xl p-4 flex flex-col overflow-hidden shadow-md">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="h-4 w-4 text-purple-400" /> Cryptographic Audit Ledger
              </span>
              <span className="text-[10px] text-slate-400 font-mono">SHA-256 Chained</span>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2 pt-3 pr-1 text-xs">
              {auditLogs.length === 0 ? (
                <p className="text-slate-500 text-center py-6 text-xs">No audit events recorded yet.</p>
              ) : (
                auditLogs.slice(0, 20).map((log) => (
                  <div key={log.id} className="p-2.5 rounded bg-[#080d1a] border border-slate-800/80 text-[11px] space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-300">{log.event_type}</span>
                      <span className={`text-[9px] font-mono px-1.5 py-0.2 rounded ${
                        log.status === 'SUCCESS' ? 'text-emerald-400 bg-emerald-500/10' :
                        log.status === 'REJECTED' ? 'text-rose-400 bg-rose-500/10' :
                        log.status === 'PENDING_APPROVAL' ? 'text-amber-400 bg-amber-500/10' :
                        'text-blue-400 bg-blue-500/10'
                      }`}>
                        {log.status}
                      </span>
                    </div>
                    <p className="text-slate-400">{log.summary}</p>
                    <div className="text-[9px] font-mono text-slate-600 truncate pt-0.5">
                      HASH: {log.cryptographic_hash}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

        </section>

      </main>
    </div>
  );
}
