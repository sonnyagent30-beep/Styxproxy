import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://bunche.railway.app';

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ tx_ref: string }> }
) {
  try {
    const { tx_ref } = await params;
    const response = await fetch(`${API_BASE_URL}/orders/${tx_ref}/rotate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });

    const data = await response.json().catch(() => ({}));
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error in /api/orders/[tx_ref]/rotate:', error);
    return NextResponse.json({ error: 'Failed to rotate proxy' }, { status: 500 });
  }
}