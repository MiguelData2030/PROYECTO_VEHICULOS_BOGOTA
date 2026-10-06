/** Display names and colours for sales / social channels. */
export const CANAL_INFO: Record<string, { label: string; cls: string; color: string }> = {
  instagram: { label: 'Instagram', cls: 'bg-pink-500/15 text-pink-300', color: '#ec4899' },
  facebook: { label: 'Facebook', cls: 'bg-blue-500/15 text-blue-300', color: '#3b82f6' },
  tiktok: { label: 'TikTok', cls: 'bg-cyan-500/15 text-cyan-300', color: '#22d3ee' },
  whatsapp: { label: 'WhatsApp', cls: 'bg-green-500/15 text-green-300', color: '#22c55e' },
  web: { label: 'Web', cls: 'bg-primary/15 text-primary', color: '#d4a843' },
  tucarro: { label: 'TuCarro', cls: 'bg-yellow-500/15 text-yellow-300', color: '#eab308' },
  referido: { label: 'Referido', cls: 'bg-purple-500/15 text-purple-300', color: '#a855f7' },
  vitrina: { label: 'Vitrina', cls: 'bg-orange-500/15 text-orange-300', color: '#f97316' },
};

export function canalInfo(canal: string) {
  return CANAL_INFO[canal] ?? { label: canal, cls: 'bg-gray-500/15 text-gray-300', color: '#9ca3af' };
}
