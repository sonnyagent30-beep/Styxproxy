import { NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'https://bunche.railway.app';

export async function GET() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/charon/weights`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return NextResponse.json({ weights: {} });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ weights: {} });
  }
}
