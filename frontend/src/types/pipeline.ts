export const STAGE_ORDER = [
  'ingest',
  'narrative',
  'voiceover',
  'editing',
  'packaging',
  'analytics',
  'completed'
] as const;

export type PipelineStage = (typeof STAGE_ORDER)[number];

export interface PipelineStageSnapshot {
  stage: PipelineStage;
  status: string;
  detail?: string | null;
  payload?: Record<string, unknown> | null;
}

export type PipelineRunStatus = 'queued' | 'running' | 'completed' | 'error';

export interface PipelineRunResponse {
  run_name: string;
  stages: PipelineStageSnapshot[];
  outputs: Record<string, unknown>;
}

export interface PipelineRunRequest {
  run_name: string;
  platforms: string[];
  stock_keywords: string[];
  notes?: string;
}

export interface PipelineRunTriggerResponse {
  run_id: string;
}

export interface PipelineRunStatusResponse {
  run_id: string;
  run_name: string;
  status: PipelineRunStatus;
  stages: PipelineStageSnapshot[];
  outputs: Record<string, unknown>;
}
