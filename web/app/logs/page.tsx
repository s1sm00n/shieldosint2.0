// web/app/logs/page.tsx
'use client';
import { useEffect, useState } from 'react';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!);

export default function LogsPage() {
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    // Подписываемся на таблицу system_logs
    const channel = supabase
      .channel('logs-stream')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'system_logs' }, (payload) => {
        setLogs((prev) => [payload.new, ...prev]);
      })
      .subscribe();
    return () => { supabase.removeChannel(channel); };
  }, []);

  return (
    <main className="bg-black min-h-screen p-4 font-mono text-xs text-green-500">
      <h2 className="text-white mb-4">SYSTEM DEBUG CONSOLE</h2>
      {logs.map((log) => (
        <div key={log.id} className="mb-1">
          <span className="text-gray-500">[{log.created_at}]</span> {log.message}
        </div>
      ))}
    </main>
  );
}
