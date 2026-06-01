/**
 * Conexão WebSocket de realtime do board (padrão BFF).
 *
 * O browser não conhece o token de sessão (ele vive num cookie httpOnly). Para
 * abrir o WebSocket, pedimos ao servidor do Next um TICKET efêmero (válido por
 * segundos) via /api/auth/ws-ticket e o usamos uma única vez na URL de conexão.
 *
 * Reconecta automaticamente com backoff. Degrada graciosamente: se o WS não
 * conectar, o app continua funcionando (só sem atualização ao vivo).
 */
import { requestWsTicket } from "./api";

export interface BoardEvent {
  event: string;
  payload: Record<string, unknown>;
}

function wsBaseUrl(): string {
  const api =
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";
  return api.replace(/^http/, "ws");
}

export function connectBoard(
  projectId: number | null,
  onEvent: (e: BoardEvent) => void,
): () => void {
  let ws: WebSocket | null = null;
  let closedByUs = false;
  let retry = 0;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  const open = async () => {
    if (closedByUs) return;
    let ticket: string;
    try {
      ticket = (await requestWsTicket()).ticket;
    } catch {
      scheduleReconnect();
      return;
    }
    if (closedByUs) return;

    const params = new URLSearchParams({ token: ticket });
    if (projectId != null) params.set("project_id", String(projectId));
    const url = `${wsBaseUrl()}/ws/board?${params.toString()}`;

    try {
      ws = new WebSocket(url);
    } catch {
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      retry = 0;
      if (closedByUs) {
        try {
          ws?.close();
        } catch {
          /* noop */
        }
      }
    };

    ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data) as BoardEvent;
        if (data.event && data.event !== "ping") {
          onEvent(data);
        }
      } catch {
        // ignora mensagens malformadas
      }
    };

    ws.onclose = () => {
      if (!closedByUs) scheduleReconnect();
    };

    ws.onerror = () => {
      // Deixa o onclose decidir o reconnect.
    };
  };

  const scheduleReconnect = () => {
    if (closedByUs) return;
    retry += 1;
    const delay = Math.min(1000 * 2 ** retry, 15000); // backoff até 15s
    reconnectTimer = setTimeout(() => void open(), delay);
  };

  void open();

  // Função de cleanup.
  return () => {
    closedByUs = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (!ws) return;
    if (ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
  };
}
