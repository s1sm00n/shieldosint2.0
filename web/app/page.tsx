'use client';
import { useEffect, useState } from 'react';
import { createClient } from '@supabase/supabase-js';

// Используем значения по умолчанию, если переменные окружения не подтянулись
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co',
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'placeholder'
);

export default function Dashboard() {
  const [status, setStatus] = useState('Loading...');

  useEffect(() => {
    async function checkDb() {
      try {
        const { data, error } = await supabase.from('incidents').select('count', { count: 'exact', head: true });
        if (error) throw error;
        setStatus('БД подключена успешно!');
      } catch (e) {
        setStatus('Ошибка подключения к БД');
      }
    }
    checkDb();
  }, []);

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>AI Media Watch</h1>
      <p>Статус системы: {status}</p>
    </div>
  );
}
