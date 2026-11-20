// API client for CloudArchSim backend
const API_BASE = 'http://localhost:8000/api';

export async function getArchitectures() {
  const res = await fetch(`${API_BASE}/architectures`);
  if (!res.ok) throw new Error('Failed to fetch architectures');
  return res.json();
}

export async function getScenarios() {
  const res = await fetch(`${API_BASE}/scenarios`);
  if (!res.ok) throw new Error('Failed to fetch scenarios');
  return res.json();
}

export async function runSimulation(architecture: string, scenario: string) {
  const res = await fetch(`${API_BASE}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ architecture, scenario }),
  });
  if (!res.ok) throw new Error('Simulation failed');
  return res.json();
}

export async function compareArchitectures(
  architecture_a: string,
  architecture_b: string,
  scenario: string
) {
  const res = await fetch(`${API_BASE}/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ architecture_a, architecture_b, scenario }),
  });
  if (!res.ok) throw new Error('Comparison failed');
  return res.json();
}
