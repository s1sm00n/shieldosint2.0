// web/app/page.tsx
import Link from 'next/link';

export default async function Page() {
  // Тут код из прошлого шага с карточками incidents
  // Добавь ссылку на логи в верхнюю часть страницы:
  return (
    <main className="bg-neutral-950 min-h-screen p-8 text-white">
      <nav className="flex justify-between mb-10">
        <h1 className="text-3xl font-bold text-red-500">🛡️ ShieldOSINT Incidents</h1>
        <Link href="/logs" className="text-neutral-400 hover:text-white underline">Открыть системные логи →</Link>
      </nav>
      {/* ... здесь твой код вывода карточек ... */}
    </main>
  );
}
