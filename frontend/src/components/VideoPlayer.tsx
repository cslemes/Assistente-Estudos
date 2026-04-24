import { useEffect, useRef } from 'react';

interface VideoPlayerProps {
  videoUrl: string;
  seekTo?: number;
}

function extractVideoId(url: string): string | null {
  // https://youtu.be/ID  or  https://youtu.be/ID?t=123
  const shortMatch = url.match(/youtu\.be\/([a-zA-Z0-9_-]{11})/);
  if (shortMatch) return shortMatch[1];

  // https://www.youtube.com/watch?v=ID  or  ...&t=123
  const longMatch = url.match(/[?&]v=([a-zA-Z0-9_-]{11})/);
  if (longMatch) return longMatch[1];

  return null;
}

export default function VideoPlayer({ videoUrl, seekTo }: VideoPlayerProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const videoId = extractVideoId(videoUrl);
  const embedSrc = videoId
    ? `https://www.youtube.com/embed/${videoId}?enablejsapi=1&origin=http://localhost:3000`
    : null;

  useEffect(() => {
    if (seekTo === undefined || seekTo <= 0 || !iframeRef.current?.contentWindow) return;
    iframeRef.current.contentWindow.postMessage(
      JSON.stringify({ event: 'command', func: 'seekTo', args: [seekTo, true] }),
      '*',
    );
  }, [seekTo]);

  if (!embedSrc) {
    return (
      <div className="w-full aspect-video bg-slate-800 flex items-center justify-center rounded-lg border border-slate-700">
        <p className="text-slate-400 text-sm">URL de vídeo inválida</p>
      </div>
    );
  }

  return (
    <div className="w-full aspect-video bg-black rounded-lg overflow-hidden">
      <iframe
        ref={iframeRef}
        src={embedSrc}
        title="YouTube video player"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
        className="w-full h-full border-0"
      />
    </div>
  );
}
