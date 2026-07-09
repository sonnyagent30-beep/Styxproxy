import { NextRequest, NextResponse } from 'next/server';

const API = process.env.NEXT_PUBLIC_API_URL || 'https://bunche.railway.app';

export async function GET(req: NextRequest, { params }: { params: Promise<{ tx_ref: string }> }) {
  try {
    const { tx_ref } = await params;
    const res = await fetch(`${API}/orders/${tx_ref}`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: 'Failed to fetch order' }, { status: 500 });
  }
}
