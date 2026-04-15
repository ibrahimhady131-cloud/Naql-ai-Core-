"use client";

import { useState, useEffect } from "react";
import { useQuery, gql } from "@apollo/client";
import { X, Play, Pause, RotateCcw, CreditCard, CheckCircle, Loader2 } from "lucide-react";

const FINTRACK_BASE_URL = process.env.NEXT_PUBLIC_FINTRACK_URL ?? "http://localhost:8004";

const AI_REASONING_QUERY = gql`
  query GetAIReasoning($shipmentId: String!) {
    aiReasoning(shipmentId: $shipmentId) {
      step
      thought
      action
      timestamp
    }
  }
`;

const TRIP_HISTORY_QUERY = gql`
  query GetTripHistory($shipmentId: String!) {
    tripHistory(shipmentId: $shipmentId) {
      timestamp
      latitude
      longitude
      speedKmh
      heading
    }
  }
`;

interface AIReasoningStep {
  step: number;
  thought: string;
  action: string;
  timestamp: string;
}

interface TripPoint {
  timestamp: string;
  latitude: number;
  longitude: number;
  speedKmh: number;
  heading: number;
}

interface LifecycleSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  shipmentId?: string;
  truckId?: string;
  truckStatus?: string;
}

const STATUS_STEPS = [
  { key: "requested", label: "Requested", icon: "1" },
  { key: "ai_matching", label: "AI Matching", icon: "2" },
  { key: "assigned", label: "Assigned", icon: "3" },
  { key: "in_transit", label: "In Transit", icon: "4" },
  { key: "delivered", label: "Delivered", icon: "5" },
];

function getCurrentStep(status: string | undefined): number {
  if (!status) return 0;
  const statusMap: Record<string, number> = {
    pending: 0,
    requested: 0,
    matching: 1,
    ai_matching: 1,
    assigned: 2,
    accepted: 2,
    in_transit: 3,
    en_route: 3,
    delivered: 4,
    completed: 4,
  };
  return statusMap[status.toLowerCase()] ?? 0;
}

export default function LifecycleSidebar({
  isOpen,
  onClose,
  shipmentId,
  truckId,
  truckStatus,
}: LifecycleSidebarProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackIndex, setPlaybackIndex] = useState(0);
  const [paymentLoading, setPaymentLoading] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState(false);
  const [paymentLink, setPaymentLink] = useState<string | null>(null);

  const { data: reasoningData, loading: reasoningLoading } = useQuery(AI_REASONING_QUERY, {
    variables: { shipmentId },
    skip: !shipmentId,
  });

  const { data: historyData, loading: historyLoading } = useQuery(TRIP_HISTORY_QUERY, {
    variables: { shipmentId },
    skip: !shipmentId,
  });

  const reasoningSteps: AIReasoningStep[] = reasoningData?.aiReasoning ?? [];
  const tripHistory: TripPoint[] = historyData?.tripHistory ?? [];

  const currentStep = getCurrentStep(truckStatus);
  const invoiceAmount = 719.22; // Mock amount - in real app, fetch from GraphQL

  useEffect(() => {
    if (isPlaying && tripHistory.length > 0) {
      const interval = setInterval(() => {
        setPlaybackIndex((prev) => (prev + 1) % tripHistory.length);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [isPlaying, tripHistory.length]);

  const handleReplay = () => {
    setPlaybackIndex(0);
    setIsPlaying(true);
  };

  const handlePayNow = async () => {
    setPaymentLoading(true);
    try {
      const params = new URLSearchParams({
        invoice_id: shipmentId ?? "mock-invoice",
        amount_egp: String(invoiceAmount),
        user_id: "mock-user",
        payment_method: "paymob",
      });
      const resp = await fetch(`${FINTRACK_BASE_URL}/api/v1/payments/link?${params.toString()}`, {
        method: "POST",
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data?.detail ?? "Failed to create payment link");
      }
      setPaymentLink(data?.url ?? null);
      setPaymentSuccess(true);
    } catch (e) {
      setPaymentLink(null);
      setPaymentSuccess(false);
    } finally {
      setPaymentLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed right-0 top-0 h-full w-96 bg-gray-900 border-l border-gray-800 shadow-2xl z-[1001] overflow-y-auto">
      <div className="p-4 border-b border-gray-800 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Shipment Details</h2>
        <button onClick={onClose} className="p-1 hover:bg-gray-800 rounded">
          <X className="w-5 h-5 text-gray-400" />
        </button>
      </div>

      <div className="p-4 space-y-6">
        {truckId && (
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-sm text-gray-400">Truck ID</p>
            <p className="text-white font-mono text-sm">{truckId.slice(0, 8)}...</p>
          </div>
        )}

        {/* Payment Section */}
        <div>
          <h3 className="text-sm font-medium text-gray-400 mb-3">Payment</h3>
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-gray-400">Invoice Amount</span>
              <span className="text-white font-bold">{invoiceAmount.toFixed(2)} EGP</span>
            </div>
            
            {!paymentSuccess ? (
              <button
                onClick={handlePayNow}
                disabled={paymentLoading}
                className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white py-2 px-4 rounded-lg transition-colors"
              >
                {paymentLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <CreditCard className="w-4 h-4" />
                    <span>Pay Now</span>
                  </>
                )}
              </button>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-green-400">
                  <CheckCircle className="w-4 h-4" />
                  <span className="text-sm">Payment Link Generated</span>
                </div>
                <a
                  href={paymentLink || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full text-center bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg text-sm transition-colors"
                >
                  Open Payment Portal
                </a>
              </div>
            )}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-medium text-gray-400 mb-3">Status Timeline</h3>
          <div className="space-y-2">
            {STATUS_STEPS.map((step, index) => (
              <div
                key={step.key}
                className={`flex items-center gap-3 p-2 rounded-lg ${
                  index <= currentStep ? "bg-blue-900/30" : "bg-gray-800/50"
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    index < currentStep
                      ? "bg-green-500 text-white"
                      : index === currentStep
                      ? "bg-blue-500 text-white"
                      : "bg-gray-600 text-gray-300"
                  }`}
                >
                  {index < currentStep ? "!" : step.icon}
                </div>
                <span
                  className={`text-sm ${
                    index <= currentStep ? "text-white" : "text-gray-500"
                  }`}
                >
                  {step.label}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-medium text-gray-400 mb-3">AI Reasoning</h3>
          {reasoningLoading ? (
            <div className="text-gray-500 text-sm">Loading AI thoughts...</div>
          ) : reasoningSteps.length > 0 ? (
            <div className="space-y-3">
              {reasoningSteps.map((step) => (
                <div key={step.step} className="bg-gray-800 rounded-lg p-3 border-l-2 border-blue-500">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold text-blue-400">Step {step.step}</span>
                    <span className="text-xs text-gray-500">{step.action}</span>
                  </div>
                  <p className="text-sm text-gray-300">{step.thought}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-gray-800 rounded-lg p-4">
              <p className="text-gray-500 text-sm">
                No AI reasoning available yet. Shipment is being processed...
              </p>
              <div className="mt-3 space-y-2">
                <div className="flex items-center gap-2 text-gray-600">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                  <span className="text-xs">Analyzing truck capacity...</span>
                </div>
                <div className="flex items-center gap-2 text-gray-600">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                  <span className="text-xs">Calculating route optimization...</span>
                </div>
                <div className="flex items-center gap-2 text-gray-600">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                  <span className="text-xs">Evaluating driver ratings...</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {tripHistory.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-gray-400">Trip Playback</h3>
              <div className="flex gap-2">
                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="p-1.5 bg-gray-800 hover:bg-gray-700 rounded"
                >
                  {isPlaying ? (
                    <Pause className="w-4 h-4 text-white" />
                  ) : (
                    <Play className="w-4 h-4 text-white" />
                  )}
                </button>
                <button
                  onClick={handleReplay}
                  className="p-1.5 bg-gray-800 hover:bg-gray-700 rounded"
                >
                  <RotateCcw className="w-4 h-4 text-white" />
                </button>
              </div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4">
              <p className="text-sm text-gray-400 mb-2">
                Position {playbackIndex + 1} of {tripHistory.length}
              </p>
              {tripHistory[playbackIndex] && (
                <div className="space-y-1 text-xs text-gray-300">
                  <p>Lat: {tripHistory[playbackIndex].latitude.toFixed(4)}</p>
                  <p>Lng: {tripHistory[playbackIndex].longitude.toFixed(4)}</p>
                  <p>Speed: {tripHistory[playbackIndex].speedKmh.toFixed(0)} km/h</p>
                </div>
              )}
              <div className="mt-3 h-1 bg-gray-700 rounded overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${((playbackIndex + 1) / tripHistory.length) * 100}%` }}
                ></div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
