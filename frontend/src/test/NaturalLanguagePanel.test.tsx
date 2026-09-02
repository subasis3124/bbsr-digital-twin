import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { NaturalLanguagePanel } from '../components/NaturalLanguagePanel';
import { ApiService } from '../services/api';

vi.mock('../services/api', () => ({
  ApiService: {
    sendAIQuery: vi.fn(),
  },
}));

window.HTMLElement.prototype.scrollIntoView = vi.fn();

describe('NaturalLanguagePanel Component Suite', () => {
  it('renders correctly when open and displays initial welcome message', () => {
    render(<NaturalLanguagePanel isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByText('Digital Twin AI Assistant')).toBeInTheDocument();
    expect(screen.getByText(/Ask questions about flood risks, traffic forecasts/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Ask AI assistant in natural language...')).toBeInTheDocument();
  });

  it('does not render when isOpen is false', () => {
    const { container } = render(<NaturalLanguagePanel isOpen={false} onClose={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('triggers sendAIQuery when submitting a prompt', async () => {
    const mockResponse = {
      query_id: 'test-qid',
      query: 'Show me high flood-risk areas',
      answer: 'Identified 20 high flood-risk cells in Ward 20.',
      intent: 'FLOOD_RISK_QUERY',
      response_type: 'feature_list' as const,
      tool_calls: [{ tool: 'get_flood_risk', parameters: { risk_level: 'HIGH' } }],
      tool_results: [{ tool: 'get_flood_risk', success: true }],
      map_actions: [{ action: 'set_layer_visibility', layer: 'floodRisk', visible: true }],
      provenance: {
        data_sources: ['Flood Risk ML Engine'],
        model_type: 'RandomForest_FloodRisk_v1',
        timestamp: '2026-09-02T22:00:00Z',
        is_synthetic: true,
        scientific_validation_warning: 'WARNING: Synthetic flood data active.'
      },
      warnings: [],
      suggested_followups: ['Simulate rainfall in Ward 20'],
      created_at: '2026-09-02T22:00:00Z'
    };

    (ApiService.sendAIQuery as any).mockResolvedValueOnce(mockResponse);

    const onDispatch = vi.fn();
    render(<NaturalLanguagePanel isOpen={true} onClose={vi.fn()} onDispatchMapAction={onDispatch} />);

    const input = screen.getByPlaceholderText('Ask AI assistant in natural language...');
    fireEvent.change(input, { target: { value: 'Show me high flood-risk areas' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(screen.getByText('Identified 20 high flood-risk cells in Ward 20.')).toBeInTheDocument();
    });

    expect(screen.getByText('Intent: FLOOD_RISK_QUERY')).toBeInTheDocument();
    expect(screen.getByText('Tool: get_flood_risk')).toBeInTheDocument();
    expect(screen.getByText('SYNTHETIC')).toBeInTheDocument();
    expect(onDispatch).toHaveBeenCalledWith({ action: 'set_layer_visibility', layer: 'floodRisk', visible: true });
  });

  it('sends prompt when clicking quick prompt button', async () => {
    (ApiService.sendAIQuery as any).mockResolvedValueOnce({
      query_id: 'q-2',
      query: 'Show me high flood-risk areas',
      answer: 'Flood query executed.',
      intent: 'FLOOD_RISK_QUERY',
      response_type: 'text' as const,
      tool_calls: [],
      tool_results: [],
      map_actions: [],
      provenance: {
        data_sources: ['Open-Meteo'],
        model_type: 'mock',
        timestamp: '2026-09-02T22:00:00Z',
        is_synthetic: true
      },
      warnings: [],
      suggested_followups: [],
      created_at: '2026-09-02T22:00:00Z'
    });

    render(<NaturalLanguagePanel isOpen={true} onClose={vi.fn()} />);

    const quickBtn = screen.getByText('Show me high flood-risk areas');
    fireEvent.click(quickBtn);

    await waitFor(() => {
      expect(screen.getByText('Flood query executed.')).toBeInTheDocument();
    });
  });
});
