import { useEffect, useState } from 'react';
import { API_BASE_URL } from '../api/client';
import {
  PipelineRunResponse,
  PipelineRunStatus,
  PipelineStageSnapshot,
  STAGE_ORDER
} from '../types/pipeline';

const stageOrderIndex = STAGE_ORDER.reduce<Record<string, number>>((acc, stage, index) => {
  acc[stage] = index;
  return acc;
}, {});

const sortSnapshots = (snapshots: PipelineStageSnapshot[]) => {
  return [...snapshots].sort((a, b) => stageOrderIndex[a.stage] - stageOrderIndex[b.stage]);
};

const updateStageSnapshot = (
  snapshots: PipelineStageSnapshot[],
  snapshot: PipelineStageSnapshot
) => {
  const filtered = snapshots.filter((existing) => existing.stage !== snapshot.stage);
  return sortSnapshots([...filtered, snapshot]);
};

interface RunStreamState {
  runId: string | null;
  runName: string | null;
  status: PipelineRunStatus | null;
  stages: PipelineStageSnapshot[];
  outputs: Record<string, unknown>;
  error: string | null;
}

const defaultState: RunStreamState = {
  runId: null,
  runName: null,
  status: null,
  stages: [],
  outputs: {},
  error: null
};

export const useRunStream = (runId: string | null) => {
  const [state, setState] = useState<RunStreamState>({ ...defaultState });

  useEffect(() => {
    if (!runId) {
      setState({ ...defaultState });
      return;
    }

    setState({
      runId,
      runName: null,
      status: 'queued',
      stages: [],
      outputs: {},
      error: null
    });

    const eventSource = new EventSource(`${API_BASE_URL}/v1/pipeline/run/${runId}/stream`);
    let closedManually = false;

    const closeStream = () => {
      if (!closedManually) {
        closedManually = true;
        eventSource.close();
      }
    };

    eventSource.onmessage = (event) => {
      if (!event.data) {
        return;
      }

      try {
        const payload = JSON.parse(event.data) as Record<string, unknown>;
        const eventType = payload.event as string | undefined;

        if (eventType === 'init') {
          const stages = Array.isArray(payload.stages)
            ? (payload.stages as PipelineStageSnapshot[])
            : [];
          setState((prev) => ({
            ...prev,
            runName: (payload.run_name as string | undefined) ?? prev.runName,
            stages: sortSnapshots(stages)
          }));
          return;
        }

        if (eventType === 'run') {
          const status = payload.status as PipelineRunStatus | undefined;
          setState((prev) => ({
            ...prev,
            status: status ?? prev.status ?? 'queued'
          }));
          return;
        }

        if (eventType === 'stage') {
          const snapshot = payload.snapshot as PipelineStageSnapshot | undefined;
          if (!snapshot) {
            return;
          }
          setState((prev) => ({
            ...prev,
            stages: updateStageSnapshot(prev.stages, snapshot)
          }));
          return;
        }

        if (eventType === 'complete') {
          const response = payload.response as PipelineRunResponse | undefined;
          if (response) {
            setState({
              runId,
              runName: response.run_name,
              status: 'completed',
              stages: sortSnapshots(response.stages ?? []),
              outputs: response.outputs ?? {},
              error: null
            });
          } else {
            setState((prev) => ({
              ...prev,
              status: 'completed'
            }));
          }
          closeStream();
          return;
        }

        if (eventType === 'error') {
          setState((prev) => ({
            ...prev,
            status: 'error',
            error: (payload.message as string | undefined) ?? 'Pipeline run failed'
          }));
          closeStream();
        }
      } catch {
        setState((prev) => ({
          ...prev,
          error: prev.error ?? 'Malformed pipeline update'
        }));
      }
    };

    eventSource.onerror = () => {
      if (closedManually) {
        return;
      }
      setState((prev) => ({
        ...prev,
        error: prev.error ?? 'Connection interrupted'
      }));
    };

    return () => {
      closeStream();
    };
  }, [runId]);

  return state;
};
