import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'CloudArchSim — Cloud Architecture Simulation Platform',
  description:
    'A local cloud architecture simulation and visualization platform. Select a scenario and architecture to observe how different cloud setups behave under traffic loads, failures, and auto-scaling events.',
  keywords: ['cloud', 'simulation', 'architecture', 'networking', 'visualization'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased bg-[#0a0f1e] text-slate-100">{children}</body>
    </html>
  );
}
