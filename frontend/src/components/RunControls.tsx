import { FormEvent, useState } from 'react';
import { usePipelineRun } from '../hooks/usePipelineRun';
import type { PipelineRunTriggerResponse } from '../types/pipeline';

interface RunControlsProps {
  onRunTriggered: (runId: string) => void;
  isRunActive?: boolean;
}

export function RunControls({ onRunTriggered, isRunActive = false }: RunControlsProps) {
  const [keywords, setKeywords] = useState('luxury education, neuroscience learning, family campus');
  const [notes, setNotes] = useState('Highlight bespoke programs and private tour CTA.');
  const mutation = usePipelineRun();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    mutation.mutate(
      {
        run_name: `demo-${Date.now()}`,
        platforms: ['instagram', 'tiktok'],
        stock_keywords: keywords.split(',').map((keyword: string) => keyword.trim()),
        notes
      },
      {
        onSuccess: (data: PipelineRunTriggerResponse) => onRunTriggered(data.run_id)
      }
    );
  };

  return (
    <form onSubmit={handleSubmit} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-primary">Pipeline</h2>
      <p className="mt-1 text-sm text-slate-500">
        Configure creative guidance and trigger the autonomous pipeline.
      </p>
      <label className="mt-4 block text-sm font-medium text-primary" htmlFor="keywords">
        Stock Keywords
      </label>
      <textarea
        id="keywords"
        className="mt-2 w-full rounded-lg border border-slate-300 bg-white p-3 text-sm focus:border-primary focus:outline-none"
        rows={3}
        value={keywords}
        onChange={(event) => setKeywords(event.target.value)}
      />
      <label className="mt-4 block text-sm font-medium text-primary" htmlFor="notes">
        Creative Notes
      </label>
      <textarea
        id="notes"
        className="mt-2 w-full rounded-lg border border-slate-300 bg-white p-3 text-sm focus:border-primary focus:outline-none"
        rows={3}
        value={notes}
        onChange={(event) => setNotes(event.target.value)}
      />
      <button
        type="submit"
        className="mt-6 inline-flex items-center justify-center rounded-full bg-primary px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-primary/90"
        disabled={mutation.isPending || isRunActive}
      >
        {mutation.isPending || isRunActive ? 'Pipeline Running…' : 'Launch Pipeline'}
      </button>
    </form>
  );
}
