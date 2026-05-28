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

// ── Notes APIs ────────────────────────────────────────────────────

export async function generateNotes(playlistId, noteType = 'detailed', videoId = null) {
  const res = await api.post('/api/notes/generate', {
    playlist_id: playlistId,
    note_type: noteType,
    video_id: videoId,
  });
  return res.data;
}

export async function getNotes(playlistId) {
  const res = await api.get(`/api/notes/${playlistId}`);
  return res.data;
}

// ── Flashcard APIs ────────────────────────────────────────────────

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
  return `${API_BASE}/api/export/pdf/${playlistId}`;
}

// ── Health ────────────────────────────────────────────────────────

export async function healthCheck() {
  const res = await api.get('/api/health');
  return res.data;
}

export default api;
