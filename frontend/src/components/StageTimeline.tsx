import clsx from 'clsx';
import { format } from 'date-fns';
import { STAGE_ORDER } from '../types/pipeline';
import type { PipelineStageSnapshot } from '../types/pipeline';

interface StageTimelineProps {
  stages: PipelineStageSnapshot[];
}

const stageLabels: Record<(typeof STAGE_ORDER)[number], string> = {
  ingest: 'Ingest',
  narrative: 'Narrative',
  voiceover: 'Voiceover',
  editing: 'Editing',
  packaging: 'Packaging',
  analytics: 'Analytics',
  completed: 'Completed'
};

const statusColors: Record<string, string> = {
  done: 'bg-secondary text-primary',
  running: 'bg-primary text-white',
  queued: 'bg-slate-200 text-slate-600',
  pending: 'bg-slate-200 text-slate-600',
  error: 'bg-red-100 text-red-600'
};

const renderDetail = (snapshot: PipelineStageSnapshot) => {
  if (!snapshot.detail) {
    return null;
  }

  if (snapshot.stage === 'completed') {
    const match = snapshot.detail.match(/Run finished at (.+)/);
    if (match) {
      const parsed = new Date(match[1]);
      if (!Number.isNaN(parsed.getTime())) {
        return `Run finished ${format(parsed, 'PPPp')}`;
      }
    }
  }

  return snapshot.detail;
};

export function StageTimeline({ stages }: StageTimelineProps) {
  return (
    <div className="grid gap-3">
      {STAGE_ORDER.map((stage) => {
        const snapshot = stages.find((s) => s.stage === stage) ?? {
          stage,
          status: 'queued',
          detail: 'Awaiting execution'
        };
        const colorClass = statusColors[snapshot.status] ?? statusColors.queued;
        return (
          <div
            key={stage}
            className={clsx(
              'rounded-lg border border-slate-200 p-4 transition-colors',
              snapshot.status === 'done' && 'shadow-sm'
            )}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-primary">
                {stageLabels[stage]}
              </h3>
              <span
                className={clsx(
                  'rounded-full px-3 py-1 text-xs font-medium uppercase',
                  colorClass
                )}
              >
                {snapshot.status}
              </span>
            </div>
            {snapshot.detail && (
              <p className="mt-2 text-sm text-slate-600">{renderDetail(snapshot)}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
