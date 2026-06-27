'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function LandingPage() {
  const router = useRouter()
  const [ageConfirmed, setAgeConfirmed] = useState(false)

  return (
    <main className="flex flex-col items-center justify-center min-h-screen gap-8 bg-zinc-950 text-white">
      <h1 className="text-5xl font-bold tracking-tight">Boredroom</h1>
      <p className="text-zinc-400 text-lg">Two strangers. One canvas.</p>
      <label className="flex items-center gap-3 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={ageConfirmed}
          onChange={(e) => setAgeConfirmed(e.target.checked)}
          className="w-5 h-5 cursor-pointer"
        />
        <span className="text-zinc-300 text-sm">I am 18 years of age or older</span>
      </label>
      <button
        disabled={!ageConfirmed}
        onClick={() => router.push('/waiting')}
        className="px-8 py-3 rounded-full bg-white text-zinc-950 font-semibold text-base disabled:opacity-40 disabled:cursor-not-allowed hover:bg-zinc-100 transition-colors"
      >
        Start
      </button>
    </main>
  )
}
