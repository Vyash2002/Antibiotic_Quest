// Thin wrapper around the Flask JSON API.
export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

async function request(method, url, data) {
  let res;
  try {
    res = await fetch(url, {
      method,
      headers: data ? { "Content-Type": "application/json" } : {},
      body: data ? JSON.stringify(data) : undefined,
    });
  } catch (e) {
    throw new ApiError("network", 0);
  }
  let json = {};
  try { json = await res.json(); } catch (e) { /* empty body */ }
  if (!res.ok) throw new ApiError(json.error || `Request failed (${res.status})`, res.status);
  return json;
}

export const api = {
  config: () => request("GET", "/api/config"),
  createParticipant: (d) => request("POST", "/api/participants", d),
  saveTest: (phase, d) => request("POST", `/api/tests/${phase}`, d),
  startLevel: (level, d) => request("POST", `/api/levels/${level}/start`, d),
  answer: (d) => request("POST", "/api/answer", d),
  endLevel: (level, d) => request("POST", `/api/levels/${level}/end`, d),
  endSession: (d) => request("POST", "/api/sessions/end", d),
  results: (pid) => request("GET", `/api/results/${encodeURIComponent(pid)}`),
};
