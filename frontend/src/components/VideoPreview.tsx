import { useMemo } from 'react';
import { API_BASE_URL } from '../api/client';

interface VideoPreviewProps {
  title: string;
  description: string;
  videoPath?: string;
  caption?: string;
  hashtags?: string[];
}

export function VideoPreview({ title, description, videoPath, caption, hashtags }: VideoPreviewProps) {
  const resolvedVideoSrc = useMemo(() => {
    if (!videoPath) {
      return undefined;
    }
    if (/^https?:\/\//i.test(videoPath)) {
      return videoPath;
    }
    const normalizedPath = videoPath.replace(/^\/+/, '');
    return `${API_BASE_URL}/${normalizedPath}`;
  }, [videoPath]);

  return (
    <div className="flex flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-primary">{title}</h2>
          <p className="text-sm text-slate-500">{description}</p>
        </div>
      </div>
      <div className="mt-4 aspect-[9/16] w-full max-h-[400px] overflow-hidden rounded-lg bg-secondary/60">
        {resolvedVideoSrc ? (
          <video controls className="h-full w-full object-cover">
            <source src={resolvedVideoSrc} type="video/mp4" />
            Your browser does not support the video tag.
          </video>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-primary/80">
            Generated preview will appear here.
          </div>
        )}
      </div>
      {caption && (
        <div className="mt-4">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-primary">Caption</h3>
          <p className="mt-2 text-sm text-slate-700">{caption}</p>
        </div>
      )}
      {hashtags && hashtags.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-primary">Hashtags</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {hashtags.map((tag) => (
              <span key={tag} className="rounded-full bg-secondary px-3 py-1 text-xs font-medium text-primary">
                #{tag.replace('#', '')}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
