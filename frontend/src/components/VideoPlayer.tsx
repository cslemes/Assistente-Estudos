import { useCallback, useEffect, useRef, useState } from 'react';
import { Dropdown, Slider, Tooltip, Typography } from 'antd';
import {
  ExpandOutlined,
  LoadingOutlined,
  PauseCircleFilled,
  PlayCircleFilled,
  ShrinkOutlined,
  SoundOutlined,
  StepBackwardOutlined,
  StepForwardOutlined,
} from '@ant-design/icons';
import { fetchSegments } from '../api';
import type { Segment } from '../types';

const { Text } = Typography;

interface VideoPlayerProps {
  videoUrl: string;
  seekTo?: number;
  lessonId?: number;
}

const SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];

function formatDuration(secs: number): string {
  if (!isFinite(secs) || isNaN(secs)) return '0:00';
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = Math.floor(secs % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function extractYouTubeId(url: string): string | null {
  const m = url.match(/youtu\.be\/([a-zA-Z0-9_-]{11})/) ?? url.match(/[?&]v=([a-zA-Z0-9_-]{11})/);
  return m ? m[1] : null;
}

// Minimal YT IFrame API types
interface YTPlayer {
  playVideo(): void;
  pauseVideo(): void;
  seekTo(seconds: number, allowSeekAhead: boolean): void;
  setVolume(vol: number): void;
  mute(): void;
  unMute(): void;
  setPlaybackRate(rate: number): void;
  getCurrentTime(): number;
  getDuration(): number;
  getVideoLoadedFraction(): number;
  getPlayerState(): number;
  destroy(): void;
}
interface YTEvent { data: number; target: YTPlayer; }
interface YTPlayerOptions {
  videoId: string;
  width: string;
  height: string;
  playerVars?: Record<string, number | string>;
  events?: {
    onReady?: (e: YTEvent) => void;
    onStateChange?: (e: YTEvent) => void;
    onError?: (e: YTEvent) => void;
  };
}

declare global {
  interface Window {
    YT?: { Player: new (el: HTMLElement, opts: YTPlayerOptions) => YTPlayer; PlayerState: Record<string, number> };
    onYouTubeIframeAPIReady?: () => void;
  }
}

let ytApiLoading = false;
let ytApiReady = false;
const ytReadyCallbacks: (() => void)[] = [];

function loadYTApi(cb: () => void) {
  if (ytApiReady) { cb(); return; }
  ytReadyCallbacks.push(cb);
  if (ytApiLoading) return;
  ytApiLoading = true;
  window.onYouTubeIframeAPIReady = () => {
    ytApiReady = true;
    ytReadyCallbacks.forEach((f) => f());
    ytReadyCallbacks.length = 0;
  };
  const s = document.createElement('script');
  s.src = 'https://www.youtube.com/iframe_api';
  document.head.appendChild(s);
}

export default function VideoPlayer({ videoUrl, seekTo, lessonId }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const ytContainerRef = useRef<HTMLDivElement>(null);
  const ytPlayerRef = useRef<YTPlayer | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [buffered, setBuffered] = useState(0);
  const [volume, setVolume] = useState(1);
  const [muted, setMuted] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showControls, setShowControls] = useState(true);
  const [fullscreen, setFullscreen] = useState(false);
  const [scrubbing, setScrubbing] = useState(false);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [captionsOn, setCaptionsOn] = useState(true);
  const [captionsAvailable, setCaptionsAvailable] = useState<boolean | null>(null); // null = loading

  const youtubeId = extractYouTubeId(videoUrl);
  const isYouTube = !!youtubeId;

  // Fetch transcript segments for real-time captions (AbortController guards against stale responses)
  useEffect(() => {
    if (!lessonId) { setCaptionsAvailable(false); return; }
    const ctrl = new AbortController();
    setCaptionsAvailable(null);
    setSegments([]);
    fetchSegments(lessonId)
      .then((data) => {
        if (ctrl.signal.aborted) return;
        setSegments(data);
        setCaptionsAvailable(data.length > 0);
      })
      .catch(() => {
        if (ctrl.signal.aborted) return;
        setSegments([]);
        setCaptionsAvailable(false);
      });
    return () => ctrl.abort();
  }, [lessonId]);

  // --- YouTube IFrame API ---
  useEffect(() => {
    if (!isYouTube || !youtubeId) return;
    setLoading(true);
    setError(null);

    loadYTApi(() => {
      if (!ytContainerRef.current) return;
      const player = new window.YT!.Player(ytContainerRef.current, {
        videoId: youtubeId,
        width: '100%',
        height: '100%',
        playerVars: {
          controls: 0,
          modestbranding: 1,
          rel: 0,
          disablekb: 1,
          iv_load_policy: 3,
          autoplay: 0,
          origin: window.location.origin,
        },
        events: {
          onReady: (e) => {
            setDuration(e.target.getDuration());
            setLoading(false);
            // Poll current time every 150 ms for smooth captions + progress bar
            pollTimer.current = setInterval(() => {
              const yt = ytPlayerRef.current;
              if (!yt) return;
              setCurrentTime(yt.getCurrentTime());
              setBuffered(yt.getVideoLoadedFraction() * 100);
            }, 150);
          },
          onStateChange: (e) => {
            const state = e.data;
            // -1 unstarted, 0 ended, 1 playing, 2 paused, 3 buffering, 5 cued
            if (state === 1) { setPlaying(true); setLoading(false); }
            else if (state === 2 || state === 0) { setPlaying(false); setLoading(false); }
            else if (state === 3) { setLoading(true); }
            if (state === 0) setDuration(e.target.getDuration()); // refresh on end
          },
          onError: () => { setError('Não foi possível carregar o vídeo.'); setLoading(false); },
        },
      });
      ytPlayerRef.current = player;
    });

    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
      ytPlayerRef.current?.destroy();
      ytPlayerRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [youtubeId]);

  // Sync controlled props to YT player
  useEffect(() => {
    const yt = ytPlayerRef.current;
    if (!yt) return;
    if (playing) yt.playVideo(); else yt.pauseVideo();
  }, [playing]);

  useEffect(() => {
    const yt = ytPlayerRef.current;
    if (!yt) return;
    yt.setVolume(muted ? 0 : Math.round(volume * 100));
    if (muted) yt.mute(); else yt.unMute();
  }, [volume, muted]);

  useEffect(() => {
    ytPlayerRef.current?.setPlaybackRate(speed);
    if (videoRef.current) videoRef.current.playbackRate = speed;
  }, [speed]);

  // Seek from external prop (transcript deep-link)
  useEffect(() => {
    if (seekTo === undefined) return;
    if (isYouTube) {
      ytPlayerRef.current?.seekTo(seekTo, true);
      setPlaying(true);
    } else {
      const v = videoRef.current;
      if (!v) return;
      v.currentTime = seekTo;
      v.play().catch(() => null);
    }
  }, [seekTo, isYouTube]);

  // Fullscreen listener
  useEffect(() => {
    const onFsChange = () => setFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', onFsChange);
    return () => document.removeEventListener('fullscreenchange', onFsChange);
  }, []);

  const resetHideTimer = useCallback(() => {
    setShowControls(true);
    if (hideTimer.current) clearTimeout(hideTimer.current);
    hideTimer.current = setTimeout(() => {
      if (!scrubbing) setShowControls(false);
    }, 3000);
  }, [scrubbing]);

  function togglePlay() {
    if (isYouTube) {
      setPlaying((p) => !p);
    } else {
      const v = videoRef.current;
      if (!v) return;
      if (v.paused) v.play().catch(() => null); else v.pause();
    }
  }

  function toggleMute() { setMuted((m) => !m); }

  function onVolumeChange(val: number) {
    setVolume(val / 100);
    setMuted(val === 0);
  }

  function skipBy(secs: number) {
    if (isYouTube) {
      const yt = ytPlayerRef.current;
      if (!yt) return;
      const next = Math.max(0, Math.min(yt.getDuration(), yt.getCurrentTime() + secs));
      yt.seekTo(next, true);
    } else {
      const v = videoRef.current;
      if (!v) return;
      v.currentTime = Math.max(0, Math.min(v.duration, v.currentTime + secs));
    }
  }

  function toggleFullscreen() {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) containerRef.current.requestFullscreen();
    else document.exitFullscreen();
  }

  function getProgressPct(e: React.MouseEvent | MouseEvent): number {
    const bar = progressRef.current;
    if (!bar) return 0;
    const rect = bar.getBoundingClientRect();
    return Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
  }

  function onProgressClick(e: React.MouseEvent<HTMLDivElement>) {
    if (!duration) return;
    const t = getProgressPct(e) * duration;
    if (isYouTube) ytPlayerRef.current?.seekTo(t, true);
    else if (videoRef.current) videoRef.current.currentTime = t;
    setCurrentTime(t);
  }

  function onProgressMouseDown(e: React.MouseEvent<HTMLDivElement>) {
    setScrubbing(true);
    onProgressClick(e);
    function onMove(ev: MouseEvent) {
      if (!duration) return;
      const t = getProgressPct(ev) * duration;
      if (isYouTube) ytPlayerRef.current?.seekTo(t, true);
      else if (videoRef.current) videoRef.current.currentTime = t;
      setCurrentTime(t);
    }
    function onUp() {
      setScrubbing(false);
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }

  if (!videoUrl) {
    return (
      <div style={placeholderStyle}>
        <Text style={{ color: '#64748b' }}>Nenhum vídeo disponível</Text>
      </div>
    );
  }

  const played = duration > 0 ? (currentTime / duration) * 100 : 0;
  const activeCaption = segments.find((s) => currentTime >= s.start && currentTime < s.end);

  const speedItems = SPEEDS.map((s) => ({
    key: String(s),
    label: <span style={{ color: s === speed ? '#38bdf8' : undefined }}>{s === 1 ? 'Normal' : `${s}×`}</span>,
    onClick: () => setSpeed(s),
  }));

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative', width: '100%', aspectRatio: '16/9',
        background: '#000', borderRadius: 8, overflow: 'hidden',
        cursor: showControls ? 'default' : 'none', userSelect: 'none',
      }}
      onMouseMove={resetHideTimer}
      onMouseLeave={() => { if (!scrubbing) setShowControls(false); }}
      onMouseEnter={() => setShowControls(true)}
    >
      {/* YouTube container */}
      {isYouTube && (
        <div ref={ytContainerRef} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} />
      )}

      {/* Native video for direct URLs */}
      {!isYouTube && (
        <video
          ref={videoRef}
          src={videoUrl}
          style={{ width: '100%', height: '100%', display: 'block', objectFit: 'contain' }}
          preload="auto"
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onEnded={() => setPlaying(false)}
          onTimeUpdate={() => {
            const v = videoRef.current;
            if (!v) return;
            setCurrentTime(v.currentTime);
            if (v.buffered.length > 0)
              setBuffered((v.buffered.end(v.buffered.length - 1) / v.duration) * 100);
          }}
          onLoadedMetadata={() => {
            if (videoRef.current) setDuration(videoRef.current.duration);
            setLoading(false);
          }}
          onWaiting={() => setLoading(true)}
          onCanPlay={() => setLoading(false)}
          onVolumeChange={() => {
            const v = videoRef.current;
            if (!v) return;
            setVolume(v.volume);
            setMuted(v.muted);
          }}
          onError={() => { setError('Não foi possível carregar o vídeo.'); setLoading(false); }}
        />
      )}

      {/* Transparent click-to-play/pause overlay */}
      <div
        style={{ position: 'absolute', inset: 0, zIndex: 1, cursor: 'pointer' }}
        onClick={togglePlay}
      />

      {loading && !error && (
        <div style={{ ...centerOverlay, color: '#38bdf8', fontSize: 32, zIndex: 2 }}>
          <LoadingOutlined />
        </div>
      )}
      {error && (
        <div style={{ ...centerOverlay, zIndex: 2 }}>
          <Text style={{ color: '#f87171', fontSize: 13 }}>{error}</Text>
        </div>
      )}

      {/* Real-time caption overlay */}
      {captionsOn && activeCaption && (
        <div
          style={{
            position: 'absolute', bottom: 68, left: '8%', right: '8%',
            textAlign: 'center', padding: '6px 16px',
            background: 'rgba(0,0,0,0.72)',
            backdropFilter: 'blur(4px)', WebkitBackdropFilter: 'blur(4px)',
            borderRadius: 6, color: '#f1f5f9', fontSize: 14, lineHeight: 1.6,
            zIndex: 3, pointerEvents: 'none',
          }}
        >
          {activeCaption.text}
        </div>
      )}

      {/* Controls overlay */}
      <div
        style={{
          position: 'absolute', bottom: 0, left: 0, right: 0,
          background: 'linear-gradient(transparent, rgba(0,0,0,0.85))',
          padding: '32px 12px 10px',
          transition: 'opacity 0.2s',
          opacity: showControls ? 1 : 0,
          pointerEvents: showControls ? 'auto' : 'none',
          zIndex: 4,
        }}
      >
        {/* Seek bar */}
        <div
          ref={progressRef}
          style={{ position: 'relative', height: 16, cursor: 'pointer', display: 'flex', alignItems: 'center' }}
          onClick={onProgressClick}
          onMouseDown={onProgressMouseDown}
        >
          <div style={{ position: 'absolute', left: 0, right: 0, height: 3, background: 'rgba(255,255,255,0.2)', borderRadius: 2 }}>
            <div style={{ position: 'absolute', left: 0, width: `${buffered}%`, height: '100%', background: 'rgba(255,255,255,0.35)', borderRadius: 2, transition: 'width 0.3s' }} />
            <div style={{ position: 'absolute', left: 0, width: `${played}%`, height: '100%', background: '#38bdf8', borderRadius: 2 }} />
          </div>
          <div style={{
            position: 'absolute', left: `${played}%`, transform: 'translateX(-50%)',
            width: 12, height: 12, background: '#38bdf8', borderRadius: '50%',
            boxShadow: '0 0 4px rgba(56,189,248,0.6)',
            transition: scrubbing ? 'none' : 'left 0.1s',
          }} />
        </div>

        {/* Button row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 4 }}>
          <Tooltip title="−10s">
            <button style={iconBtn} onClick={() => skipBy(-10)}><StepBackwardOutlined style={{ fontSize: 14 }} /></button>
          </Tooltip>

          <button style={{ ...iconBtn, fontSize: 22 }} onClick={togglePlay}>
            {playing ? <PauseCircleFilled /> : <PlayCircleFilled />}
          </button>

          <Tooltip title="+10s">
            <button style={iconBtn} onClick={() => skipBy(10)}><StepForwardOutlined style={{ fontSize: 14 }} /></button>
          </Tooltip>

          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 4 }}>
            <button style={iconBtn} onClick={toggleMute}>
              <SoundOutlined style={{ fontSize: 14, opacity: muted || volume === 0 ? 0.35 : 1 }} />
            </button>
            <div style={{ width: 64 }}>
              <Slider
                min={0} max={100}
                value={muted ? 0 : Math.round(volume * 100)}
                onChange={onVolumeChange}
                tooltip={{ open: false }}
                style={{ margin: 0 }}
                styles={{ track: { background: '#38bdf8' }, rail: { background: 'rgba(255,255,255,0.2)' } }}
              />
            </div>
          </div>

          <Text style={{ color: 'rgba(255,255,255,0.8)', fontSize: 12, fontVariantNumeric: 'tabular-nums', marginLeft: 8, whiteSpace: 'nowrap' }}>
            {formatDuration(currentTime)} / {formatDuration(duration)}
          </Text>

          <div style={{ flex: 1 }} />

          <Dropdown menu={{ items: speedItems }} trigger={['click']} placement="topRight">
            <button style={{ ...iconBtn, fontSize: 11, fontWeight: 600, minWidth: 36 }}>
              {speed === 1 ? '1×' : `${speed}×`}
            </button>
          </Dropdown>

          {/* CC toggle */}
          <Tooltip title={
            captionsAvailable === false
              ? 'Transcrição não disponível'
              : captionsOn ? 'Desativar legendas' : 'Ativar legendas'
          }>
            <button
              style={{
                ...iconBtn,
                fontSize: 10, fontWeight: 700, minWidth: 28,
                border: '1px solid',
                borderColor: captionsAvailable && captionsOn ? '#38bdf8' : 'rgba(255,255,255,0.2)',
                borderRadius: 3,
                color: captionsAvailable && captionsOn ? '#38bdf8' : 'rgba(255,255,255,0.3)',
                padding: '2px 4px',
                cursor: captionsAvailable ? 'pointer' : 'default',
                opacity: captionsAvailable === null ? 0.5 : 1,
              }}
              onClick={() => { if (captionsAvailable) setCaptionsOn((v) => !v); }}
            >
              CC
            </button>
          </Tooltip>

          <Tooltip title={fullscreen ? 'Sair da tela cheia' : 'Tela cheia'}>
            <button style={iconBtn} onClick={toggleFullscreen}>
              {fullscreen ? <ShrinkOutlined style={{ fontSize: 14 }} /> : <ExpandOutlined style={{ fontSize: 14 }} />}
            </button>
          </Tooltip>
        </div>
      </div>
    </div>
  );
}

const iconBtn: React.CSSProperties = {
  background: 'none', border: 'none', color: 'rgba(255,255,255,0.85)',
  cursor: 'pointer', padding: '4px 6px',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  borderRadius: 4, fontSize: 16, lineHeight: 1, transition: 'color 0.15s',
};

const placeholderStyle: React.CSSProperties = {
  width: '100%', aspectRatio: '16/9', background: '#1e293b',
  border: '1px solid #334155', borderRadius: 8,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
};

const centerOverlay: React.CSSProperties = {
  position: 'absolute', inset: 0,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
};
