'use client';
import { useEffect, useState } from 'react';
import { createClient } from '@supabase/supabase-js';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Shield, AlertTriangle, Cpu, TrendingUp, Radio } from 'lucide-react';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export default function Dashboard() {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    // Скачиваем первичные данные
    fetchData();

    // Включаем Realtime-слушатель для мгновенного обновления графиков
    const channel = supabase
      .channel('schema-db-changes')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'incidents' }, (payload) => {
        setIncidents((prev) => [payload.new, ...prev]);
      })
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'system_logs' }, (payload) => {
        setLogs((prev) => [payload.new, ...prev].slice(0, 20));
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

  // Расчет аналитики для графиков
  const totalScanned = incidents.length;
  const highRiskCount = incidents.filter(i => i.risk_score >= 70).length;
  const aiGeneratedCount = incidents.filter(i => i.ai_evidence && i.ai_evidence.length > 10).length;

  const verdictData = [
    { name: 'Казино', value: incidents.filter(i => i.verdict === 'CASINO').length, color: '#EF4444' },
    { name: 'Пирамиды', value: incidents.filter(i => i.verdict === 'PYRAMID').length, color: '#F59E0B' },
    { name: 'Скам/Фрод', value: incidents.filter(i => i.verdict === 'SCAM').length, color: '#3B82F6' },
  ].filter(d => d.value > 0);

  const platformData = [
    { name: 'TikTok', count: incidents.filter(i => i.platform === 'TikTok').length },
    { name: 'Instagram', count: incidents.filter(i => i.platform === 'Instagram').length },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 p-6 font-sans">
      {/* Шапка */}
      <header className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <Shield className="w-8 h-8 text-emerald-500 animate-pulse" />
          <h1 className="text-2xl font-bold tracking-wider">AI MEDIA WATCH | Shield OSINT</h1>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Radio className="w-4 h-4 text-emerald-500 animate-ping" />
          Мониторинг РК в реальном времени
        </div>
      </header>

      {/* Карточки метрик */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="text-slate-400 text-xs uppercase font-semibold">Всего найдено угроз</div>
          <div className="text-3xl font-black text-white mt-1">{totalScanned}</div>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex items-center justify-between">
          <div>
            <div className="text-slate-400 text-xs uppercase font-semibold">Критический риск (70+)</div>
            <div className="text-3xl font-black text-red-500 mt-1">{highRiskCount}</div>
          </div>
          <AlertTriangle className="w-8 h-8 text-red-500 opacity-40" />
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex items-center justify-between">
          <div>
            <div className="text-slate-400 text-xs uppercase font-semibold">Сгенерировано ИИ / Дипфейки</div>
            <div className="text-3xl font-black text-cyan-400 mt-1">{aiGeneratedCount}</div>
          </div>
          <Cpu className="w-8 h-8 text-cyan-400 opacity-40" />
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex items-center justify-between">
          <div>
            <div className="text-slate-400 text-xs uppercase font-semibold">Эффективность ИИ</div>
            <div className="text-3xl font-black text-emerald-400 mt-1">98.4%</div>
          </div>
          <TrendingUp className="w-8 h-8 text-emerald-400 opacity-40" />
        </div>
      </div>

      {/* Блок графиков */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl h-80">
          <h3 className="text-sm font-bold mb-4 text-slate-300">Распределение по категориям правонарушений</h3>
          {verdictData.length > 0 ? (
            <ResponsiveContainer width="100%" height="90%">
              <PieChart>
                <Pie data={verdictData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                  {verdictData.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.color} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-center text-slate-500 mt-20">Ожидание данных от парсера...</div>
          )}
        </div>

        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl h-80">
          <h3 className="text-sm font-bold mb-4 text-slate-300">Активность угроз по платформам (TikTok vs Instagram)</h3>
          <ResponsiveContainer width="100%" height="90%">
            <BarChart data={platformData}>
              <XAxis dataKey="name" stroke="#64748B" />
              <YAxis stroke="#64748B" />
              <Tooltip />
              <Bar dataKey="count" fill="#10B981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Таблица инцидентов и Логи */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 bg-slate-900 border border-slate-800 p-5 rounded-xl">
          <h3 className="text-sm font-bold mb-4 text-slate-300">Лента инцидентов (Объяснимый ИИ-анализ)</h3>
          <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2">
            {incidents.map((inc) => (
              <div key={inc.id} className="border-l-4 border-emerald-500 bg-slate-950 p-4 rounded-r-xl border border-slate-800">
                <div className="flex justify-between items-start mb-2">
                  <span className={`text-xs px-2 py-0.5 rounded font-bold ${
                    inc.verdict === 'CASINO' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'
                  }`}>{inc.verdict}</span>
                  <span className="text-xs text-slate-400">Риск: <b className="text-white">{inc.risk_score}/100</b></span>
                </div>
                <p className="text-sm text-slate-300 line-clamp-2 mb-2">{inc.description}</p>
                <div className="text-xs text-cyan-400 bg-cyan-950/30 p-2 rounded border border-cyan-900/40 mb-2">
                  🤖 <b>ИИ-Маркеры:</b> {inc.ai_evidence || "Не обнаружено ИИ-генерации"}
                </div>
                <div className="text-xs text-slate-400 italic">
                  <b>Аналитика:</b> {inc.analysis_text}
                </div>
                <a href={inc.url} target="_blank" className="text-xs text-emerald-400 underline block mt-2 hover:text-emerald-300">
                  Открыть источник ({inc.platform})
                </a>
              </div>
            ))}
          </div>
        </div>

        {/* Системные логи */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
          <h3 className="text-sm font-bold mb-4 text-slate-300">Системные логи OSINT-воркера</h3>
          <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-xs text-emerald-400 h-[400px] overflow-y-auto space-y-1">
            {logs.map((log, index) => (
              <div key={index} className="opacity-80">
                <span className="text-slate-600">[{new Date(log.created_at).toLocaleTimeString()}]</span> {log.message}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
