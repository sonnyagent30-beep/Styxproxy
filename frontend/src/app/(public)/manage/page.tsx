import { redirect } from 'next/navigation';

export default function ManagePage() {
  redirect('/order/status');
}
