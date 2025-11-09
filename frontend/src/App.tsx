import { useState } from 'react';
import { RunControls } from './components/RunControls';
import { StageTimeline } from './components/StageTimeline';
import { VideoPreview } from './components/VideoPreview';
import { useRunStream } from './hooks/useRunStream';
import type { PipelineStageSnapshot } from './types/pipeline';

function App() {
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const runState = useRunStream(activeRunId);
  const isRunActive = runState.status === 'queued' || runState.status === 'running';

  const handleRunTriggered = (runId: string) => {
    setActiveRunId(runId);
  };

  const stages: PipelineStageSnapshot[] = runState.stages ?? [];
  const instagramOutput = (runState.outputs.instagram ?? {}) as Record<string, unknown>;
  const tiktokOutput = (runState.outputs.tiktok ?? {}) as Record<string, unknown>;

  const instagramHashtags = Array.isArray(instagramOutput.hashtags)
    ? (instagramOutput.hashtags as string[])
    : undefined;
  const tiktokHashtags = Array.isArray(tiktokOutput.hashtags)
    ? (tiktokOutput.hashtags as string[])
    : undefined;

  return (
    <div className="min-h-screen bg-[#F8F9FF]">
      <header className="border-b border-secondary/70 bg-white/60 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-6">
          <h1 className="text-3xl font-semibold text-primary">
            Media Generation Dashboard
          </h1>
        </div>
      </header>

      <main className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-8 xl:flex-row">
        <div className="flex flex-col gap-6 xl:w-1/3">
          <RunControls onRunTriggered={handleRunTriggered} isRunActive={isRunActive} />
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-brand">
            <h2 className="text-lg font-semibold text-primary">Agent State Timeline</h2>
            <p className="mt-1 text-sm text-slate-500">
              Each stage reflects an autonomous capability executed during the run.
            </p>
            {runState.runId && (
              <div className="mt-3 flex items-center justify-between text-xs uppercase tracking-wide text-slate-500">
                <span>Run: {runState.runName ?? runState.runId}</span>
                {runState.status && (
                  <span
                    className="rounded-full border border-slate-200 px-3 py-1 text-[11px] font-semibold text-primary"
                  >
                    {runState.status.toUpperCase()}
                  </span>
                )}
              </div>
            )}
            {runState.error && (
              <p className="mt-3 text-sm text-red-500">{runState.error}</p>
            )}
            <div className="mt-4">
              <StageTimeline stages={stages} />
            </div>
          </div>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 xl:w-2/3">
          <VideoPreview
            title="Instagram Story"
            description="Luxury narrative tailored for parent decision-makers."
            videoPath={typeof instagramOutput.video_path === 'string' ? instagramOutput.video_path : undefined}
            caption={typeof instagramOutput.caption === 'string' ? instagramOutput.caption : undefined}
            hashtags={instagramHashtags}
          />
          <VideoPreview
            title="TikTok Cut"
            description="Hook-driven highlight optimized for virality."
            videoPath={typeof tiktokOutput.video_path === 'string' ? tiktokOutput.video_path : undefined}
            caption={typeof tiktokOutput.caption === 'string' ? tiktokOutput.caption : undefined}
            hashtags={tiktokHashtags}
          />
        </div>
      </main>
    </div>
  );
}

export default App;
