/**
 * API client for Ytutor AI backend.
 */

import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000, // 2 min for long operations
  headers: { 'Content-Type': 'application/json' },
});

// Add a request interceptor to attach JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('ytutor_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Auth APIs ─────────────────────────────────────────────────────

export async function login(email, password) {
  // OAuth2 token endpoint expects form-urlencoded payload
  const params = new URLSearchParams();
  params.append('username', email);
  params.append('password', password);
  
  const res = await api.post('/api/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  });
  return res.data;
}

export async function signup(email, username, password) {
  const res = await api.post('/api/auth/signup', { email, username, password });
  return res.data;
}

export async function getMe() {
  const res = await api.get('/api/auth/me');
  return res.data;
}

export async function forgotPassword(email) {
  const res = await api.post('/api/auth/forgot-password', { email });
  return res.data;
}

export async function resetPassword(email, otp, newPassword) {
  const res = await api.post('/api/auth/reset-password', {
    email,
    otp,
    new_password: newPassword,
  });
  return res.data;
}

// ── Playlist APIs ─────────────────────────────────────────────────

export async function importPlaylist(playlistUrl) {
  const res = await api.post('/api/playlist/import', { playlist_url: playlistUrl });
  return res.data;
}

export async function getPlaylists() {
  const res = await api.get('/api/playlists');
  return res.data;
}

export async function getPlaylist(playlistId) {
  const res = await api.get(`/api/playlist/${playlistId}`);
  return res.data;
}

export async function getPlaylistStatus(playlistId) {
  const res = await api.get(`/api/playlist/${playlistId}/status`);
  return res.data;
}

export async function deletePlaylist(playlistId) {
  const res = await api.delete(`/api/playlist/${playlistId}`);
  return res.data;
}

// ── Chat APIs ─────────────────────────────────────────────────────

export async function chatQuery(playlistId, message) {
  const res = await api.post('/api/chat/query', {
    playlist_id: playlistId,
    message,
  });
  return res.data;
}

export async function chatQueryStream(playlistId, message, handlers = {}) {
  const token = localStorage.getItem('ytutor_token');
  const response = await fetch(`${API_BASE}/api/chat/query/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      playlist_id: playlistId,
      message,
    }),
    signal: handlers.signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`Stream request failed with status ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  const processEvent = (eventText) => {
    const dataLines = eventText
      .split('\n')
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trim());

    if (dataLines.length === 0) return;

    const payload = JSON.parse(dataLines.join('\n'));
    if (payload.error) {
      handlers.onError?.(payload.error);
      throw new Error(payload.error);
    }
    if (payload.token) {
      handlers.onToken?.(payload.token);
    }
    if (payload.done) {
      handlers.onDone?.({
        sources: payload.sources || [],
        foundContext: payload.found_context ?? false,
      });
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop() || '';

    for (const eventText of events) {
      if (eventText.trim()) processEvent(eventText);
    }
  }

  buffer += decoder.decode();
  if (buffer.trim()) processEvent(buffer);
}

export async function getChatHistory(playlistId) {
  const res = await api.get(`/api/chat/history/${playlistId}`);
  return res.data;
}

// ── Notes APIs ────────────────────────────────────────────────────

export async function generateNotes(playlistId, noteType = 'detailed', videoId = null) {
  const res = await api.post('/api/notes/generate', {
    playlist_id: playlistId,
    note_type: noteType,
    video_id: videoId,
  });
  return res.data;
}

export async function getNotesJobStatus(jobId) {
  const res = await api.get(`/api/notes/status/${jobId}`);
  return res.data;
}

export async function getNotes(playlistId) {
  const res = await api.get(`/api/notes/${playlistId}`);
  return res.data;
}

// ── Flashcard APIs ────────────────────────────────────────────────

export async function getVoiceNotes() {
  const res = await api.get('/api/voice-notes');
  return res.data;
}

export async function getVoiceNote(voiceNoteId) {
  const res = await api.get(`/api/voice-notes/${voiceNoteId}`);
  return res.data;
}

export async function transcribeVoiceNote(audioBlob, title = '') {
  const form = new FormData();
  form.append('title', title);
  form.append('audio', audioBlob, audioBlob.name || 'voice-note.webm');
  const res = await api.post('/api/voice-notes/transcribe', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 600000,
  });
  return res.data;
}

export async function organizeVoiceNote(voiceNoteId, rawTranscript, title = '') {
  const res = await api.post(`/api/voice-notes/${voiceNoteId}/organize`, {
    raw_transcript: rawTranscript,
    title,
  }, {
    timeout: 600000,
  });
  return res.data;
}

export async function deleteVoiceNote(voiceNoteId) {
  const res = await api.delete(`/api/voice-notes/${voiceNoteId}`);
  return res.data;
}

export async function downloadVoiceNotePdf(voiceNoteId) {
  const res = await api.get(`/api/voice-notes/${voiceNoteId}/export/pdf`, {
    responseType: 'blob',
    timeout: 120000,
  });
  return res;
}

export async function generateFlashcards(playlistId, count = 10) {
  const res = await api.post('/api/flashcards/generate', {
    playlist_id: playlistId,
    count,
  });
  return res.data;
}

export async function getFlashcards(playlistId) {
  const res = await api.get(`/api/flashcards/${playlistId}`);
  return res.data;
}

// ── Quiz APIs ─────────────────────────────────────────────────────

export async function generateQuiz(playlistId, count = 10) {
  const res = await api.post('/api/quiz/generate', {
    playlist_id: playlistId,
    count,
  });
  return res.data;
}

export async function getQuiz(playlistId) {
  const res = await api.get(`/api/quiz/${playlistId}`);
  return res.data;
}

// ── Export APIs ────────────────────────────────────────────────────

export function getExportPdfUrl(playlistId) {
  const url = new URL(`${API_BASE}/api/export/pdf/${playlistId}`);
  // In a real app we'd pass token via a signed URL or cookie for file downloads,
  // but for simplicity, we rely on the backend checking headers.
  // Wait, the backend requires Authorization header. A direct browser link won't send it.
  // We'll update the export button to fetch the blob via Axios instead.
  return url.toString();
}

// ── Health ────────────────────────────────────────────────────────

export async function healthCheck() {
  const res = await api.get('/api/health');
  return res.data;
}

export default api;
