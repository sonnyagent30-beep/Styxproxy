import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://bunche.railway.app';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ tx_ref: string }> }
) {
  try {
    const { tx_ref } = await params;
    
    const response = await fetch(`${API_BASE_URL}/orders/${tx_ref}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Order not found' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching order:', error);
    return NextResponse.json(
      { error: 'Failed to fetch order' },
      { status: 500 }
    );
  }
}
