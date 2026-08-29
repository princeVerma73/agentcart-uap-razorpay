import React, { useState, useEffect, useRef } from 'react';
import { 
  Bot, ShieldCheck, ShoppingCart, Zap, AlertTriangle, CheckCircle, 
  Terminal, Lock, RefreshCw, ArrowRight, DollarSign, Database, 
  Play, FileText, Check, X, Layers, Activity, Sparkles, ChevronRight,
  TrendingUp, BarChart3, Sliders, Shield, AlertCircle, ShoppingBag,
  ExternalLink, ChevronDown, Cpu, CheckCircle2, XCircle, Clock, Package
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

const NAV_ITEMS = [
  { id: 'hero', label: 'Product', icon: Package },
  { id: 'merchant-catalog', label: 'Catalog', icon: Database },
  { id: 'analytics-section', label: 'Analytics', icon: BarChart3 },
  { id: 'policy-section', label: 'Policy & Security', icon: Shield },
  { id: 'audit-ledger', label: 'Audit Ledger', icon: FileText },
];

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
  const [activeSection, setActiveSection] = useState<string>("hero");
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

  // Track active section on scroll
  useEffect(() => {
    const handleScroll = () => {
      const scrollPosition = window.scrollY + 200;
      for (let i = NAV_ITEMS.length - 1; i >= 0; i--) {
        const section = document.getElementById(NAV_ITEMS[i].id);
        if (section && section.offsetTop <= scrollPosition) {
          setActiveSection(NAV_ITEMS[i].id);
          break;
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
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

    // Scroll smoothly to the live activity section
    const activityElement = document.getElementById('activity-feed');
    if (activityElement) {
      activityElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

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
        action: 'payment_failure_demo', 
        status: 'INFO'
      }]);
      return;
    }
    await recordCheckoutFailure(lastCheckout.sessionId, lastCheckout.orderId, 'failed');
    setSteps(prev => [...prev, {
      step_number: prev.length + 1,
      title: 'Payment Gateway Failure Safely Recorded',
      thought: `Order ${lastCheckout.orderId} remains failed; no settlement or revenue was recorded.`,
      action: 'payment_failure_simulated', 
      status: 'REJECTED'
    }]);
    setLastCheckout(null);
    fetchMerchantAnalytics();
  };

  const resetCatalog = async () => {
    await fetch('/api/catalog/reset', { method: 'POST' });
    fetchCatalog();
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex flex-col font-sans selection:bg-blue-100 selection:text-blue-900">
      
      {/* Top Clean Navigation Bar */}
      <header className="border-b border-slate-200 bg-white sticky top-0 z-40 px-4 sm:px-8 py-3.5 shadow-sm">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          
          {/* Brand & Identity */}
          <div className="flex items-center space-x-3">
            <div className="h-8 w-8 rounded-lg bg-[#0052cc] flex items-center justify-center text-white shadow-sm">
              <Bot className="h-4.5 w-4.5" />
            </div>
            <div>
              <span className="font-bold text-base sm:text-lg text-[#0c2340] tracking-tight">AgentCart</span>
              <span className="text-xs text-slate-400 ml-2 hidden md:inline font-normal">Autonomous Commerce Protocol</span>
            </div>
          </div>

          {/* Right Status & Launch CTA */}
          <div className="flex items-center space-x-2 sm:space-x-3">
            <div className="hidden sm:flex items-center space-x-2 text-xs">
              <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-700 font-medium">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>Razorpay Rails</span>
              </div>
              <div className="hidden md:flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-blue-50 border border-blue-200 text-blue-700 font-medium">
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>Policy Gate</span>
              </div>
              <div className="hidden lg:flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-slate-100 border border-slate-200 text-slate-700 font-medium">
                <Lock className="h-3.5 w-3.5" />
                <span>UAP / AP2</span>
              </div>
            </div>

            <a 
              href="#hero-card"
              onClick={() => setActiveSection('hero')}
              className="px-4 py-2 bg-[#0c83fe] hover:bg-[#0066ff] text-white text-xs sm:text-sm font-semibold rounded-lg shadow-sm transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <Play className="h-3.5 w-3.5 fill-current" />
              <span>Launch Purchase</span>
            </a>
          </div>

        </div>
      </header>

      {/* Main Page Layout: Compact Left Navigation + Centered Main Content */}
      <div className="flex-1 max-w-7xl w-full mx-auto flex flex-col md:flex-row px-4 sm:px-6 lg:px-8 gap-4 md:gap-6 lg:gap-8">
        
        {/* Compact Left Sidebar Navigation (No numbers, clean vertical stack) */}
        <aside className="md:w-40 lg:w-44 shrink-0 md:sticky md:top-16 md:self-start py-3 md:py-6 z-30">
          <div className="hidden md:block mb-2 px-2.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Navigation</span>
          </div>
          
          <nav className="flex md:flex-col gap-1 overflow-x-auto md:overflow-visible no-scrollbar pb-1 md:pb-0">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              return (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  onClick={() => setActiveSection(item.id)}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all whitespace-nowrap ${
                    isActive 
                      ? 'bg-blue-50/90 text-[#0052cc] font-semibold border-l-2 border-[#0052cc]'
                      : 'text-slate-600 hover:text-[#0c2340] hover:bg-slate-100/60 font-medium'
                  }`}
                >
                  <Icon className={`h-4 w-4 transition-colors shrink-0 ${
                    isActive ? 'text-[#0052cc]' : 'text-slate-400'
                  }`} />
                  <span className="text-[13px] sm:text-sm tracking-tight">{item.label}</span>
                </a>
              );
            })}
          </nav>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 min-w-0 py-3 md:py-6 space-y-10">
          
          {/* Hero Section: Compact, Balanced 2-line Typography */}
          <section id="hero" className="scroll-mt-20">
            
            {/* Centered Constrained Editorial Headline (ColdStream Typography) */}
            <div className="text-center max-w-2xl mx-auto pt-2 pb-6">
              
              <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-[62px] font-extrabold tracking-[-0.04em] leading-[0.98] mb-4">
                <span className="block text-[#0a192f] whitespace-nowrap animate-hero-line-1">
                  Autonomous commerce,
                </span>
                <span className="block text-slate-400 font-extrabold whitespace-nowrap animate-hero-line-2">
                  built for trust.
                </span>
              </h1>

              <p className="text-sm sm:text-base text-slate-600 leading-relaxed font-normal max-w-xl mx-auto animate-hero-desc mt-4">
                AgentCart lets AI agents discover products, make purchases, and execute payments within deterministic policy controls on Razorpay rails.
              </p>
              
              {/* Trust / Value Points */}
              <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-6 mt-4 text-xs sm:text-sm font-medium text-slate-600 animate-hero-trust">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" /> Deterministic Spending Bounds
                </span>
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" /> Human-in-the-Loop Sign-Off
                </span>
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" /> Real-time MCP Discovery
                </span>
              </div>
            </div>

            {/* Interactive Agent Purchase Intent Card */}
            <div id="hero-card" className="max-w-2xl mx-auto bg-white border border-slate-200 rounded-2xl p-5 sm:p-6 shadow-sm">
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
                <div className="flex items-center space-x-2.5">
                  <div className="h-7 w-7 rounded-lg bg-blue-50 text-[#0052cc] flex items-center justify-center">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">Agent Purchase Intent</h3>
                    <p className="text-xs text-slate-500">Enter natural language goal for autonomous agent negotiation</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs text-slate-500 font-medium">Session Pre-Auth: </span>
                  <span className="text-xs font-semibold text-slate-800">₹{policy.auto_approve_limit.toLocaleString('en-IN')}</span>
                </div>
              </div>

              {/* Input & Budget Slider */}
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Natural Language Goal
                  </label>
                  <textarea
                    value={promptGoal}
                    onChange={(e) => setPromptGoal(e.target.value)}
                    placeholder="e.g. Buy 2 braided 4K HDMI cables for office setup..."
                    rows={2}
                    className="w-full bg-slate-50 border border-slate-300 rounded-xl p-3 text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#0c83fe]/20 focus:border-[#0c83fe] transition-all resize-none font-sans"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-center bg-slate-50/80 border border-slate-200/80 rounded-xl p-3">
                  <div className="sm:col-span-4">
                    <span className="text-xs font-medium text-slate-600 block">User Budget Allocation:</span>
                    <span className="text-base font-bold text-[#0c2340]">₹{maxBudget.toLocaleString('en-IN')}</span>
                  </div>
                  <div className="sm:col-span-8 flex items-center space-x-3">
                    <span className="text-xs font-medium text-slate-400">₹1k</span>
                    <input
                      type="range"
                      min={1000}
                      max={20000}
                      step={500}
                      value={maxBudget}
                      onChange={(e) => setMaxBudget(Number(e.target.value))}
                      className="w-full accent-[#0c83fe] cursor-pointer h-2 bg-slate-200 rounded-lg appearance-none"
                    />
                    <span className="text-xs font-medium text-slate-400">₹20k</span>
                  </div>
                </div>

                {/* Action Button */}
                <button
                  onClick={() => handleRunAgent()}
                  disabled={isRunning || !promptGoal.trim()}
                  className="w-full py-2.5 px-5 bg-[#0c83fe] hover:bg-[#0066ff] disabled:opacity-50 text-white font-semibold rounded-xl text-sm flex items-center justify-center space-x-2 shadow-sm transition-all cursor-pointer"
                >
                  {isRunning ? (
                    <>
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      <span>Agent Transacting with Razorpay Protocol...</span>
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 fill-white" />
                      <span>Execute Autonomous Purchase</span>
                    </>
                  )}
                </button>
              </div>

              {/* Quick Demo Scenarios */}
              <div className="mt-4 pt-3 border-t border-slate-100">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-700">Pre-configured Evaluation Scenarios:</span>
                  <span className="text-[11px] text-slate-400">Click to execute</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
                  
                  <button
                    onClick={() => {
                      const g = "Buy 2 braided 4K HDMI cables for office setup";
                      setPromptGoal(g);
                      setMaxBudget(3000);
                      handleRunAgent(g, 3000);
                    }}
                    className="text-left p-2.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 transition-all hover:border-blue-300 hover:shadow-sm cursor-pointer"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-emerald-700 flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3" /> Scenario 1
                      </span>
                      <span className="text-[9px] uppercase font-mono px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">Pre-Auth</span>
                    </div>
                    <div className="text-xs font-medium text-slate-900">4K HDMI Cables</div>
                    <p className="text-[11px] text-slate-500 mt-0.5">Auto-approved under ₹3,000</p>
                  </button>

                  <button
                    onClick={() => {
                      const g = "Purchase 1 Keychron K2 mechanical keyboard";
                      setPromptGoal(g);
                      setMaxBudget(8000);
                      handleRunAgent(g, 8000);
                    }}
                    className="text-left p-2.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 transition-all hover:border-amber-300 hover:shadow-sm cursor-pointer"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-amber-700 flex items-center gap-1">
                        <AlertTriangle className="h-3 w-3" /> Scenario 2
                      </span>
                      <span className="text-[9px] uppercase font-mono px-1.5 py-0.2 rounded bg-amber-50 text-amber-700 border border-amber-200">HITL Gate</span>
                    </div>
                    <div className="text-xs font-medium text-slate-900">Keychron Keyboard</div>
                    <p className="text-[11px] text-slate-500 mt-0.5">Triggers sign-off request</p>
                  </button>

                  <button
                    onClick={() => {
                      const g = "Restock 2kg dark roast coffee beans for pantry";
                      setPromptGoal(g);
                      setMaxBudget(5000);
                      handleRunAgent(g, 5000);
                    }}
                    className="text-left p-2.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 transition-all hover:border-blue-300 hover:shadow-sm cursor-pointer"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-blue-700 flex items-center gap-1">
                        <ShoppingBag className="h-3 w-3" /> Scenario 3
                      </span>
                      <span className="text-[9px] uppercase font-mono px-1.5 py-0.2 rounded bg-blue-50 text-blue-700 border border-blue-200">B2B Pantry</span>
                    </div>
                    <div className="text-xs font-medium text-slate-900">Coffee Restock</div>
                    <p className="text-[11px] text-slate-500 mt-0.5">Multi-unit recurring order</p>
                  </button>

                  <button
                    onClick={() => {
                      const g = "Order 2 Logitech MX Master 3S mice";
                      setPromptGoal(g);
                      setMaxBudget(15000);
                      handleRunAgent(g, 15000);
                    }}
                    className="text-left p-2.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 transition-all hover:border-rose-300 hover:shadow-sm cursor-pointer"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-rose-700 flex items-center gap-1">
                        <XCircle className="h-3 w-3" /> Scenario 4
                      </span>
                      <span className="text-[9px] uppercase font-mono px-1.5 py-0.2 rounded bg-rose-50 text-rose-700 border border-rose-200">Ceiling</span>
                    </div>
                    <div className="text-xs font-medium text-slate-900">Hard Policy Block</div>
                    <p className="text-[11px] text-slate-500 mt-0.5">Exceeds ceiling (&gt;₹10,000)</p>
                  </button>

                </div>
              </div>
            </div>
          </section>

          {/* Section: Live Agent Reasoning & Execution Timeline */}
          <section id="activity-feed" className="scroll-mt-20">
            
            {/* HITL Urgent Sign-off Banner (When Pending) */}
            {pendingHitl && (
              <div className="mb-6 bg-amber-50 border border-amber-300 rounded-xl p-4 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-start space-x-3">
                    <div className="p-2 rounded-lg bg-amber-100 text-amber-800">
                      <AlertTriangle className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <h3 className="font-bold text-slate-900 text-sm">Human-in-the-Loop Sign-off Required</h3>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-amber-200 text-amber-900 font-semibold">
                          High-Value Verification
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                        This transaction of <strong className="text-slate-900">₹{pendingHitl.verifiedTotal.toLocaleString('en-IN')}</strong> exceeds the autonomous pre-authorization threshold of ₹{policy.auto_approve_limit.toLocaleString('en-IN')}. Verify Merchant details to proceed.
                      </p>
                      <div className="flex items-center space-x-4 mt-1.5 text-xs font-medium text-slate-700">
                        <span>Merchant: <strong className="text-slate-900">CloudGear Technologies</strong></span>
                        <span>Verified Total: <strong className="text-emerald-700 font-bold">₹{pendingHitl.verifiedTotal.toLocaleString('en-IN')}</strong></span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 sm:self-center">
                    <button
                      onClick={handleApproveHitl}
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg flex items-center justify-center space-x-1 shadow-sm transition-all cursor-pointer"
                    >
                      <Check className="h-3.5 w-3.5" />
                      <span>Approve &amp; Settle</span>
                    </button>
                    <button
                      onClick={() => setPendingHitl(null)}
                      className="px-3 py-2 bg-white hover:bg-slate-100 text-slate-700 text-xs font-medium rounded-lg border border-slate-300 transition-colors cursor-pointer"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Activity / Timeline Card */}
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <div className="flex items-center space-x-2">
                  <div className="h-6 w-6 rounded bg-blue-50 text-[#0052cc] flex items-center justify-center">
                    <Activity className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-slate-900">Live Agent Reasoning &amp; Execution Timeline</h2>
                  </div>
                </div>
                {activeSessionId && (
                  <div className="flex items-center space-x-2">
                    <span className="text-[11px] text-slate-500 font-medium hidden sm:inline">Session ID:</span>
                    <span className="font-mono text-xs font-semibold text-slate-700 bg-white border border-slate-200 px-2 py-0.5 rounded">
                      {activeSessionId}
                    </span>
                  </div>
                )}
              </div>

              <div className="p-5">
                {steps.length === 0 ? (
                  <div className="py-10 text-center text-slate-400">
                    <Bot className="h-8 w-8 mx-auto mb-1.5 text-slate-300" />
                    <p className="text-sm font-medium text-slate-600">No active agent transaction running.</p>
                    <p className="text-xs text-slate-400 mt-0.5">Submit an agent purchase goal or pick an evaluation scenario above.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {steps.map((step, idx) => (
                      <div 
                        key={idx} 
                        className={`p-3.5 rounded-lg border transition-all ${
                          step.status === 'SUCCESS' ? 'bg-emerald-50/40 border-emerald-200' :
                          step.status === 'REJECTED' ? 'bg-rose-50/40 border-rose-200' :
                          step.status === 'PENDING_APPROVAL' ? 'bg-amber-50/40 border-amber-200' :
                          step.status === 'RECOVERING' ? 'bg-purple-50/40 border-purple-200' :
                          'bg-slate-50/80 border-slate-200'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center space-x-2">
                            <span className="h-4.5 w-4.5 rounded-full bg-slate-200 text-slate-700 text-[10px] font-bold flex items-center justify-center">
                              {step.step_number}
                            </span>
                            <h4 className="text-xs sm:text-sm font-semibold text-slate-900">{step.title}</h4>
                          </div>
                          <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full ${
                            step.status === 'SUCCESS' ? 'bg-emerald-100 text-emerald-800' :
                            step.status === 'REJECTED' ? 'bg-rose-100 text-rose-800' :
                            step.status === 'PENDING_APPROVAL' ? 'bg-amber-100 text-amber-800' :
                            step.status === 'RECOVERING' ? 'bg-purple-100 text-purple-800' :
                            'bg-blue-100 text-blue-800'
                          }`}>
                            {step.status}
                          </span>
                        </div>
                        
                        <p className="text-xs text-slate-700 leading-relaxed font-normal pl-6">{step.thought}</p>
                        
                        {/* Contextual Upsell Option */}
                        {step.data?.upsell_candidate && (
                          <div className="mt-2.5 ml-6 p-2.5 rounded-lg bg-white border border-blue-200 text-xs space-y-1.5 shadow-sm">
                            <div className="flex items-center justify-between text-[#0052cc] font-semibold">
                              <span className="flex items-center gap-1.5">
                                <Sparkles className="h-3 w-3" /> Contextual Upsell Upgrade Option
                              </span>
                              <span className="font-bold">+₹{step.data.upsell_candidate.price_delta.toLocaleString('en-IN')}</span>
                            </div>
                            <p className="text-slate-600">{step.data.upsell_candidate.reason}</p>
                            <div className="flex items-center space-x-2 pt-0.5">
                              <button
                                onClick={() => handleGrowthInteract('upsell', 'accept', step.data.upsell_candidate.upsell_product.id, step.data.upsell_candidate.base_product_id, step.data.upsell_candidate.quantity)}
                                className="px-2.5 py-1 bg-[#0c83fe] hover:bg-[#0066ff] text-white rounded text-xs font-semibold transition-colors cursor-pointer"
                              >
                                Accept Upgrade
                              </button>
                              <button
                                onClick={() => handleGrowthInteract('upsell', 'reject', step.data.upsell_candidate.upsell_product.id, step.data.upsell_candidate.base_product_id, step.data.upsell_candidate.quantity)}
                                className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded text-xs font-medium transition-colors cursor-pointer"
                              >
                                Decline
                              </button>
                            </div>
                          </div>
                        )}

                        {/* Compatible Cross-Sell Option */}
                        {step.data?.cross_sell_candidate && (
                          <div className="mt-2.5 ml-6 p-2.5 rounded-lg bg-white border border-purple-200 text-xs space-y-1.5 shadow-sm">
                            <div className="flex items-center justify-between text-purple-700 font-semibold">
                              <span className="flex items-center gap-1.5">
                                <ShoppingCart className="h-3 w-3" /> Compatible Cross-Sell Add-On
                              </span>
                              <span className="font-bold">+₹{step.data.cross_sell_candidate.additional_price.toLocaleString('en-IN')}</span>
                            </div>
                            <p className="text-slate-600">{step.data.cross_sell_candidate.reason}</p>
                            <div className="flex items-center space-x-2 pt-0.5">
                              <button
                                onClick={() => handleGrowthInteract('cross_sell', 'accept', step.data.cross_sell_candidate.cross_sell_product.id, step.data.cross_sell_candidate.base_product_id, step.data.cross_sell_candidate.quantity)}
                                className="px-2.5 py-1 bg-purple-600 hover:bg-purple-700 text-white rounded text-xs font-semibold transition-colors cursor-pointer"
                              >
                                Add to Cart
                              </button>
                              <button
                                onClick={() => handleGrowthInteract('cross_sell', 'reject', step.data.cross_sell_candidate.cross_sell_product.id, step.data.cross_sell_candidate.base_product_id, step.data.cross_sell_candidate.quantity)}
                                className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded text-xs font-medium transition-colors cursor-pointer"
                              >
                                Decline
                              </button>
                            </div>
                          </div>
                        )}

                        {/* Razorpay Order Receipt */}
                        {step.data?.order && (
                          <div className="mt-2.5 ml-6 p-2.5 rounded-lg bg-white border border-emerald-200 text-xs space-y-1 shadow-sm">
                            <div className="text-emerald-700 font-semibold flex items-center gap-1.5">
                              <CheckCircle2 className="h-3.5 w-3.5" /> Razorpay Order Verified &amp; Settled: {step.data.order.id}
                            </div>
                            <div className="text-slate-700 font-medium">Verified Amount: ₹{step.data.verified_total?.toLocaleString('en-IN')}</div>
                            {step.data.settlement?.razorpay_payment_id && (
                              <div className="text-slate-500 font-mono text-[11px]">Payment ID: {step.data.settlement.razorpay_payment_id}</div>
                            )}
                          </div>
                        )}

                      </div>
                    ))}
                    <div ref={logsEndRef} />
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* Section: Catalog (Merchant Inventory & Chaos Controls) */}
          <section id="merchant-catalog" className="scroll-mt-20">
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 sm:p-6">
              
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-4 border-b border-slate-100 gap-3">
                <div>
                  <div className="flex items-center space-x-2">
                    <Database className="h-4.5 w-4.5 text-[#0052cc]" />
                    <h2 className="text-base font-bold text-slate-900">Merchant Inventory (MCP Catalog)</h2>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Live merchant inventory exposed via Model Context Protocol (MCP) to AI buyer agents.
                  </p>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={simulatePaymentFailure}
                    className="px-2.5 py-1.5 rounded-lg border border-rose-200 bg-rose-50 text-rose-700 text-xs font-semibold hover:bg-rose-100 transition-colors cursor-pointer"
                  >
                    Simulate Gateway Failure
                  </button>
                  <button 
                    onClick={resetCatalog}
                    className="text-xs text-slate-700 hover:text-slate-900 flex items-center gap-1 bg-slate-100 hover:bg-slate-200 px-2.5 py-1.5 rounded-lg font-medium transition-colors cursor-pointer"
                  >
                    <RefreshCw className="h-3 w-3" />
                    <span>Reset Store</span>
                  </button>
                </div>
              </div>

              {/* Product Catalog Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
                {products.map(p => (
                  <div 
                    key={p.id} 
                    className="bg-white border border-slate-200 rounded-lg p-3.5 hover:border-slate-300 transition-all flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{p.category}</span>
                          <h4 className="text-xs sm:text-sm font-bold text-slate-900 leading-snug">{p.name}</h4>
                        </div>
                        <span className="text-sm sm:text-base font-extrabold text-[#0c2340] whitespace-nowrap">
                          ₹{p.price.toLocaleString('en-IN')}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 line-clamp-2 mt-1">{p.description}</p>
                    </div>

                    <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs">
                      <div className="flex items-center space-x-1.5">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                          p.stock > 0 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'
                        }`}>
                          {p.stock > 0 ? `${p.stock} in stock` : 'Out of stock'}
                        </span>
                        <span className="text-[10px] text-slate-400 truncate max-w-[90px]">{p.merchant_name}</span>
                      </div>

                      {/* Chaos Action Buttons */}
                      <div className="flex items-center space-x-1">
                        <button
                          title="Simulate sudden price surge"
                          onClick={() => triggerPriceSurge(p.id, p.price)}
                          className="px-1.5 py-0.5 rounded bg-slate-100 hover:bg-amber-50 text-slate-600 hover:text-amber-700 text-[10px] font-medium border border-slate-200 transition-colors cursor-pointer"
                        >
                          +Surge
                        </button>
                        <button
                          title="Simulate item stockout"
                          onClick={() => triggerStockout(p.id)}
                          className="px-1.5 py-0.5 rounded bg-slate-100 hover:bg-rose-50 text-slate-600 hover:text-rose-700 text-[10px] font-medium border border-slate-200 transition-colors cursor-pointer"
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

          {/* Section: Analytics (Merchant Growth Analytics) */}
          <section id="analytics-section" className="scroll-mt-20">
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 sm:p-6">
              <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
                <div>
                  <div className="flex items-center space-x-2">
                    <BarChart3 className="h-4.5 w-4.5 text-[#0052cc]" />
                    <h2 className="text-base font-bold text-slate-900">Merchant Growth Analytics</h2>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Real-time autonomous commerce conversion metrics, GMV, and recommendation acceptance rates.
                  </p>
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                  <span className="text-xs font-medium text-slate-500 block">Total Settled GMV</span>
                  <span className="text-lg font-extrabold text-[#0c2340] mt-0.5 block">
                    ₹{merchantAnalytics?.gmv ? merchantAnalytics.gmv.toLocaleString('en-IN') : '0'}
                  </span>
                  <span className="text-[10px] text-emerald-600 font-medium mt-0.5 block">Settled on Razorpay</span>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                  <span className="text-xs font-medium text-slate-500 block">Sessions / Purchases</span>
                  <span className="text-lg font-extrabold text-[#0c2340] mt-0.5 block">
                    {metrics?.total_sessions || 0} / {metrics?.purchases || 0}
                  </span>
                  <span className="text-[10px] text-slate-500 font-medium mt-0.5 block">Completed orders</span>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                  <span className="text-xs font-medium text-slate-500 block">Conversion Rate</span>
                  <span className="text-lg font-extrabold text-emerald-600 mt-0.5 block">
                    {metrics?.conversion_rate || 0}%
                  </span>
                  <span className="text-[10px] text-slate-500 font-medium mt-0.5 block">Autonomous buy-in</span>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                  <span className="text-xs font-medium text-slate-500 block">Average Order Value</span>
                  <span className="text-lg font-extrabold text-[#0c2340] mt-0.5 block">
                    ₹{metrics?.average_order_value ? metrics.average_order_value.toLocaleString('en-IN') : '0'}
                  </span>
                  <span className="text-[10px] text-slate-500 font-medium mt-0.5 block">AOV per transaction</span>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                  <span className="text-xs font-medium text-slate-500 block">Incremental Revenue</span>
                  <span className="text-lg font-extrabold text-amber-600 mt-0.5 block">
                    ₹{metrics?.incremental_revenue ? metrics.incremental_revenue.toLocaleString('en-IN') : '0'}
                  </span>
                  <span className="text-[10px] text-amber-600 font-medium mt-0.5 block">Upsell &amp; cross-sell lift</span>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                  <span className="text-xs font-medium text-slate-500 block">Upsell Acceptance</span>
                  <span className="text-lg font-extrabold text-[#0052cc] mt-0.5 block">
                    {metrics?.upsell_acceptance_rate || 0}%
                  </span>
                  <span className="text-[10px] text-slate-500 font-medium mt-0.5 block">Contextual upgrades</span>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                  <span className="text-xs font-medium text-slate-500 block">Cross-Sell Acceptance</span>
                  <span className="text-lg font-extrabold text-purple-600 mt-0.5 block">
                    {metrics?.cross_sell_acceptance_rate || 0}%
                  </span>
                  <span className="text-[10px] text-slate-500 font-medium mt-0.5 block">Add-on purchases</span>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                  <span className="text-xs font-medium text-slate-500 block">HITL Gate Ratio</span>
                  <span className="text-lg font-extrabold text-blue-600 mt-0.5 block">
                    {merchantAnalytics?.hitl_gate_ratio || 0}%
                  </span>
                  <span className="text-[10px] text-slate-500 font-medium mt-0.5 block">High-value approvals</span>
                </div>

              </div>

              {/* Recovery Summary Bar */}
              {merchantAnalytics && (
                <div className="mt-3 p-2.5 rounded-lg bg-blue-50/60 border border-blue-100 flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2 text-slate-700">
                    <ShieldCheck className="h-3.5 w-3.5 text-[#0052cc]" />
                    <span className="font-medium">Stockout Auto-Recovery Fail-Safes:</span>
                  </div>
                  <span className="font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded text-[11px]">
                    {merchantAnalytics.failure_recoveries} Auto-Recoveries Executed
                  </span>
                </div>
              )}

            </div>
          </section>

          {/* Section: Policy & Security (Deterministic Policy & Security Guardrails) */}
          <section id="policy-section" className="scroll-mt-20">
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 sm:p-6">
              <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
                <div>
                  <div className="flex items-center space-x-2">
                    <Shield className="h-4.5 w-4.5 text-[#0052cc]" />
                    <h2 className="text-base font-bold text-slate-900">Deterministic Policy &amp; Security Guardrails</h2>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Pre-authorization bounds and cryptographic spend ceilings enforced before Razorpay order creation.
                  </p>
                </div>
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-100">
                  Security Gate Active
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                
                {/* Pre-Auth Slider */}
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-xs font-semibold text-slate-800">Autonomous Pre-Auth Limit (UAP)</span>
                    <span className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
                      ₹{policy.auto_approve_limit.toLocaleString('en-IN')}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mb-3">
                    Transactions under this amount execute autonomously without human prompt.
                  </p>
                  <div className="flex items-center space-x-3">
                    <span className="text-xs text-slate-400">₹500</span>
                    <input
                      type="range"
                      min={500}
                      max={3000}
                      step={500}
                      value={policy.auto_approve_limit}
                      onChange={(e) => updatePolicyConfig({ ...policy, auto_approve_limit: Number(e.target.value) })}
                      className="w-full accent-emerald-600 cursor-pointer h-2 bg-slate-200 rounded-lg appearance-none"
                    />
                    <span className="text-xs text-slate-400">₹3,000</span>
                  </div>
                </div>

                {/* Hard Spending Ceiling */}
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-xs font-semibold text-slate-800">Hard Spending Ceiling (Max Allowed)</span>
                    <span className="text-xs font-bold text-slate-900 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded">
                      ₹{policy.max_single_transaction_limit.toLocaleString('en-IN')}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mb-3">
                    Orders exceeding this threshold are blocked immediately by deterministic gate.
                  </p>
                  <div className="flex items-center space-x-3">
                    <span className="text-xs text-slate-400">₹3,000</span>
                    <input
                      type="range"
                      min={3000}
                      max={10000}
                      step={500}
                      value={policy.max_single_transaction_limit}
                      onChange={(e) => updatePolicyConfig({ ...policy, max_single_transaction_limit: Number(e.target.value) })}
                      className="w-full accent-[#0c83fe] cursor-pointer h-2 bg-slate-200 rounded-lg appearance-none"
                    />
                    <span className="text-xs text-slate-400">₹10,000</span>
                  </div>
                </div>

              </div>

              {/* Always Require Human Approval Toggle */}
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                <div>
                  <span className="text-xs font-semibold text-slate-800 block">Strict Mode: Always Require Human Approval</span>
                  <span className="text-xs text-slate-500">Require manual cryptographic sign-off for 100% of agent transactions regardless of amount.</span>
                </div>
                <input
                  type="checkbox"
                  checked={policy.require_human_approval_always}
                  onChange={(e) => updatePolicyConfig({ ...policy, require_human_approval_always: e.target.checked })}
                  className="accent-[#0c83fe] cursor-pointer h-4 w-4 rounded border-slate-300"
                />
              </div>

            </div>
          </section>

          {/* Section: Audit Ledger (Cryptographic Audit Ledger) */}
          <section id="audit-ledger" className="scroll-mt-20">
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 sm:p-6">
              <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
                <div>
                  <div className="flex items-center space-x-2">
                    <FileText className="h-4.5 w-4.5 text-[#0052cc]" />
                    <h2 className="text-base font-bold text-slate-900">Cryptographic Audit Ledger</h2>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Immutable event trail chained with SHA-256 cryptographic verification hashes.
                  </p>
                </div>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                  SHA-256 Chained
                </span>
              </div>

              <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                {auditLogs.length === 0 ? (
                  <div className="py-6 text-center text-slate-400 text-xs">
                    No cryptographic audit events recorded yet. Run a purchase scenario to inspect SHA-256 ledger.
                  </div>
                ) : (
                  auditLogs.slice(0, 20).map((log) => (
                    <div key={log.id} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1 hover:border-slate-300 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-slate-800">{log.event_type}</span>
                          <span className="text-[10px] text-slate-400">
                            {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ''}
                          </span>
                        </div>
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                          log.status === 'SUCCESS' ? 'text-emerald-800 bg-emerald-100' :
                          log.status === 'REJECTED' ? 'text-rose-800 bg-rose-100' :
                          log.status === 'PENDING_APPROVAL' ? 'text-amber-800 bg-amber-100' :
                          'text-blue-800 bg-blue-100'
                        }`}>
                          {log.status}
                        </span>
                      </div>
                      <p className="text-slate-600">{log.summary}</p>
                      <div className="text-[10px] font-mono text-slate-400 truncate pt-0.5">
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

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-6 px-4 sm:px-8 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-3">
          <div className="flex items-center space-x-2">
            <div className="h-5 w-5 rounded bg-[#0052cc] text-white flex items-center justify-center text-xs font-bold">
              AC
            </div>
            <span className="font-semibold text-slate-800">AgentCart</span>
            <span>— Autonomous Commerce on Razorpay Bounded Rails</span>
          </div>
          <div>
            <span>Deterministic Policy Controls · Universal Agentic Payments (UAP / AP2)</span>
          </div>
        </div>
      </footer>

    </div>
  );
}
