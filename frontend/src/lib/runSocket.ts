import type { RunEvent } from "./types";

// Subscribe to live run progress over WebSocket, falling back to SSE. Returns a
// disposer. The hub replays stage events so far to a late subscriber, then streams
// live updates (08 §7), so opening this after a run started still shows history.
export function subscribeRun(
  runId: string,
  onEvent: (ev: RunEvent) => void,
): () => void {
  let closed = false;
  let ws: WebSocket | null = null;
  let sse: EventSource | null = null;

  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const url = `${proto}://${window.location.host}/api/ws/runs/${runId}`;

  try {
    ws = new WebSocket(url);
    ws.onmessage = (e) => {
      if (closed) return;
      try {
        onEvent(JSON.parse(e.data) as RunEvent);
      } catch {
        /* ignore malformed frame */
      }
    };
    ws.onerror = () => {
      if (!closed && ws?.readyState !== WebSocket.OPEN) startSse();
    };
  } catch {
    startSse();
  }

  function startSse() {
    if (closed || sse) return;
    sse = new EventSource(`/api/runs/${runId}/events`);
    sse.onmessage = (e) => {
      if (closed) return;
      try {
        onEvent(JSON.parse(e.data) as RunEvent);
      } catch {
        /* ignore */
      }
    };
  }

  return () => {
    closed = true;
    ws?.close();
    sse?.close();
  };
}

export function cancelRunSocket(runId: string) {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${window.location.host}/api/ws/runs/${runId}`);
  ws.onopen = () => {
    ws.send(JSON.stringify({ type: "cancel" }));
    ws.close();
  };
}
