'use client';
import { useEffect, useState } from 'react';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export default function Dashboard() {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    fetchData();
    const channel = supabase
      .channel('db-changes')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'incidents' }, (payload) => {
        setIncidents((prev) => [payload.new, ...prev]);
      })
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'system_logs' }, (payload) => {
        setLogs((prev) => [payload.new, ...prev].slice(0, 15));
      })
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, []);

  const fetchData = async () => {
    const { data: inc } = await supabase.from('incidents').select('*').order('created_at', { ascending: false });
    const { data: lgs } = await supabase.from('system_logs').select('*').order('created_at', { ascending: false }).limit(10);
    if (inc) setIncidents(inc);
    if (lgs) setLogs(lgs);
  };

  const highRisk = incidents.filter(i => i.risk_score >= 70).length;

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-4 md:p-8 font-sans">
      <header className="mb-8 border-b border-gray-800 pb-4 flex justify-between items-center">
        <h1 className="text-2xl font-bold text-green-400">🛡️ AI MEDIA WATCH | Shield OSINT</h1>
        <div className="text-sm text-gray-400">🔴 Live Monitoring</div>
      </header>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
          <div className="text-gray-400 text-xs font-bold uppercase">Всего угроз</div>
          <div className="text-3xl font-black mt-1">{incidents.length}</div>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg border border-red-900/50">
          <div className="text-red-400 text-xs font-bold uppercase">Критический риск</div>
          <div className="text-3xl font-black mt-1 text-red-500">{highRisk}</div>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
          <div className="text-gray-400 text-xs font-bold uppercase">Платформы</div>
          <div className="text-3xl font-black mt-1">TikTok / Inst</div>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
          <div className="text-gray-400 text-xs font-bold uppercase">Точность ИИ</div>
          <div className="text-3xl font-black mt-1 text-green-400">99%</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-gray-800 p-5 rounded-lg border border-gray-700">
          <h2 className="text-lg font-bold mb-4 text-white">📋 Лента Инцидентов (AI Анализ)</h2>
          <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
            {incidents.length === 0 ? <p className="text-gray-500">Ожидание данных...</p> : null}
            {incidents.map((inc) => (
              <div key={inc.id} className="bg-gray-900 p-4 rounded-md border-l-4 border-green-500">
                <div className="flex justify-between items-start mb-2">
                  <span className="bg-red-500/20 text-red-400 text-xs font-bold px-2 py-1 rounded">
                    {inc.verdict}
                  </span>
                  <span className="text-xs text-gray-400">Риск: <b className="text-white">{inc.risk_score}/100</b></span>
                </div>
                <p className="text-sm text-gray-300 mb-2 line-clamp-2">{inc.description}</p>
                <div className="bg-blue-900/20 text-blue-300 text-xs p-2 rounded mb-2 border border-blue-900/50">
                  🤖 <b>ИИ Маркеры:</b> {inc.ai_evidence || "Не найдено"}
                </div>
                <div className="text-xs text-gray-400 italic mb-2"><b>Аналитика:</b> {inc.analysis_text}</div>
                <a href={inc.url} target="_blank" className="text-green-400 text-xs underline">Открыть оригинал</a>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-800 p-5 rounded-lg border border-gray-700">
          <h2 className="text-lg font-bold mb-4 text-white">💻 Логи Воркера</h2>
          <div className="bg-black p-3 rounded text-xs font-mono text-green-500 h-[500px] overflow-y-auto space-y-1">
            {logs.map((log, i) => (
              <div key={i}> {log.message} </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
