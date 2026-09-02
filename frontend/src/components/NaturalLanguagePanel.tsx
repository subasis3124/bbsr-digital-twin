import React, { useState, useRef, useEffect } from 'react';
import { ApiService } from '../services/api';
import { AIResponse, AIMapAction } from '../types';

interface NaturalLanguagePanelProps {
  isOpen: boolean;
  onClose: () => void;
  onDispatchMapAction?: (action: AIMapAction) => void;
  activeSpatialContext?: string;
  activeSimulationId?: string;
}

interface MessageItem {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp: string;
  response?: AIResponse;
  error?: string;
}

const QUICK_PROMPTS = [
  "Show me high flood-risk areas",
  "What is the GNN traffic forecast for Janpath?",
  "Show ambient air quality readings",
  "Which hospitals are available in Ward 20?",
  "Simulate heavy rainfall scenario",
  "Run emergency allocation for hospitals",
  "System status and KPI overview"
];

export const NaturalLanguagePanel: React.FC<NaturalLanguagePanelProps> = ({
  isOpen,
  onClose,
  onDispatchMapAction,
  activeSpatialContext,
  activeSimulationId
}) => {
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: 'welcome-msg',
      sender: 'ai',
      text: 'Welcome to the Bhubaneswar Digital Twin Natural Language AI Interface. Ask questions about flood risks, traffic forecasts, air quality, emergency resources, What-If simulations, or resource allocations.',
      timestamp: new Date().toLocaleTimeString()
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  if (!isOpen) return null;

  const handleSend = async (queryText: string) => {
    if (!queryText.trim() || loading) return;

    const userMsgId = `user-${Date.now()}`;
    const userMsg: MessageItem = {
      id: userMsgId,
      sender: 'user',
      text: queryText,
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setLoading(true);

    try {
      const res = await ApiService.sendAIQuery({
        query: queryText,
        spatial_context: activeSpatialContext,
        simulation_id: activeSimulationId
      });

      const aiMsg: MessageItem = {
        id: `ai-${Date.now()}`,
        sender: 'ai',
        text: res.answer,
        timestamp: new Date().toLocaleTimeString(),
        response: res
      };

      setMessages((prev) => [...prev, aiMsg]);

      // Automatically dispatch map actions if present
      if (res.map_actions && res.map_actions.length > 0 && onDispatchMapAction) {
        res.map_actions.forEach((act) => onDispatchMapAction(act));
      }
    } catch (err: any) {
      const errorMsg: MessageItem = {
        id: `err-${Date.now()}`,
        sender: 'ai',
        text: `Error executing query: ${err.message || 'Server error'}`,
        timestamp: new Date().toLocaleTimeString(),
        error: err.message
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed bottom-6 right-6 w-96 max-w-[calc(100vw-3rem)] h-[600px] max-h-[calc(100vh-6rem)] bg-slate-900/95 backdrop-blur-md border border-cyan-500/40 rounded-xl shadow-2xl z-50 flex flex-col overflow-hidden text-slate-100 font-sans transition-all duration-300"
      id="ai-natural-language-panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border-b border-cyan-500/30">
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 rounded-full bg-cyan-400 animate-pulse" />
          <h3 className="font-semibold text-sm tracking-wide text-cyan-300">
            Digital Twin AI Assistant
          </h3>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
            v1.0
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-cyan-300 text-lg leading-none transition-colors p-1"
          title="Close AI Assistant"
        >
          &times;
        </button>
      </div>

      {/* Spatial & Simulation Context Indicator */}
      {(activeSpatialContext || activeSimulationId) && (
        <div className="px-4 py-1.5 bg-slate-950/80 border-b border-slate-800 text-[11px] text-cyan-400 flex items-center gap-2">
          <span className="font-mono text-slate-400">Context:</span>
          {activeSpatialContext && (
            <span className="bg-cyan-950/60 text-cyan-300 px-1.5 py-0.5 rounded border border-cyan-900">
              {activeSpatialContext}
            </span>
          )}
          {activeSimulationId && (
            <span className="bg-amber-950/60 text-amber-300 px-1.5 py-0.5 rounded border border-amber-900">
              Sim: {activeSimulationId.slice(0, 8)}
            </span>
          )}
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4 text-xs scrollbar-thin scrollbar-thumb-slate-700">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${
              msg.sender === 'user' ? 'items-end' : 'items-start'
            }`}
          >
            <div
              className={`max-w-[88%] rounded-lg p-3 ${
                msg.sender === 'user'
                  ? 'bg-cyan-600 text-white rounded-br-none shadow-md'
                  : 'bg-slate-800/90 border border-slate-700 text-slate-200 rounded-bl-none shadow-sm'
              }`}
            >
              <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p>

              {/* AI Metadata & Tool Results */}
              {msg.response && (
                <div className="mt-3 pt-2 border-t border-slate-700/80 space-y-2">
                  {/* Intent & Type Badges */}
                  <div className="flex flex-wrap gap-1 items-center">
                    <span className="px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 text-[10px] uppercase tracking-wider">
                      Intent: {msg.response.intent}
                    </span>
                    {msg.response.tool_calls.map((tc, idx) => (
                      <span
                        key={idx}
                        className="px-1.5 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800 text-[10px]"
                      >
                        Tool: {tc.tool}
                      </span>
                    ))}
                  </div>

                  {/* Provenance & Warnings */}
                  {msg.response.provenance && (
                    <div className="bg-slate-900/90 p-2 rounded border border-slate-700/70 text-[10px]">
                      <div className="flex items-center justify-between text-slate-400 mb-1">
                        <span>Source: {msg.response.provenance.data_sources.join(', ')}</span>
                        {msg.response.provenance.is_synthetic && (
                          <span className="text-amber-400 font-semibold">SYNTHETIC</span>
                        )}
                      </div>
                      {msg.response.provenance.scientific_validation_warning && (
                        <p className="text-amber-300/90 italic leading-snug">
                          {msg.response.provenance.scientific_validation_warning}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Map Actions Dispatch Buttons */}
                  {msg.response.map_actions && msg.response.map_actions.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {msg.response.map_actions.map((act, idx) => (
                        <button
                          key={idx}
                          onClick={() => onDispatchMapAction && onDispatchMapAction(act)}
                          className="px-2 py-1 bg-cyan-950 hover:bg-cyan-900 border border-cyan-700 text-cyan-300 rounded text-[10px] font-medium transition-colors flex items-center gap-1"
                        >
                          <span>🗺️</span>
                          <span>
                            {act.action === 'set_layer_visibility'
                              ? `Toggle Layer (${act.layer})`
                              : act.action === 'set_flood_filter'
                              ? `Filter Flood (${act.risk})`
                              : act.action}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Follow-up Suggestions */}
                  {msg.response.suggested_followups && msg.response.suggested_followups.length > 0 && (
                    <div className="pt-2 space-y-1">
                      <span className="text-[10px] text-slate-400 font-medium">Suggested follow-ups:</span>
                      <div className="flex flex-col gap-1">
                        {msg.response.suggested_followups.map((prompt, idx) => (
                          <button
                            key={idx}
                            onClick={() => handleSend(prompt)}
                            className="text-left text-[11px] text-cyan-400 hover:text-cyan-200 hover:underline bg-slate-900/60 p-1.5 rounded border border-slate-700/50 transition-colors"
                          >
                            &rarr; {prompt}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <span className="text-[9px] text-slate-400 mt-1 block text-right">
                {msg.timestamp}
              </span>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center space-x-2 text-cyan-400 bg-slate-800/60 p-2.5 rounded-lg border border-slate-700 w-fit">
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
            <span className="text-xs">Parsing intent & executing model tools...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts Bar */}
      <div className="px-3 py-2 bg-slate-950/90 border-t border-slate-800 overflow-x-auto whitespace-nowrap scrollbar-none flex gap-1.5">
        {QUICK_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(prompt)}
            disabled={loading}
            className="px-2.5 py-1 bg-slate-800 hover:bg-cyan-950 hover:border-cyan-700 border border-slate-700 rounded-full text-[11px] text-slate-300 hover:text-cyan-300 transition-all flex-shrink-0"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Input Form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend(inputQuery);
        }}
        className="p-3 bg-slate-900 border-t border-slate-800 flex gap-2 items-center"
      >
        <input
          type="text"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          placeholder="Ask AI assistant in natural language..."
          disabled={loading}
          className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
          id="ai-natural-language-input"
        />
        <button
          type="submit"
          disabled={loading || !inputQuery.trim()}
          className="bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-medium text-xs px-4 py-2 rounded-lg transition-colors flex items-center gap-1 shadow-sm"
        >
          <span>Send</span>
        </button>
      </form>
    </div>
  );
};
