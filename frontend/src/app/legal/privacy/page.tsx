import React from 'react';
import fs from 'fs';
import path from 'path';
import Header from '@/components/Header';
import Footer from '@/components/Footer';

export default function Privacy() {
  // Read the legal document at build time (server-side)
  const legalPath = path.join(process.cwd(), '../../../../legal/PRIVACY_POLICY.md');
  let content = '';
  
  try {
    content = fs.readFileSync(legalPath, 'utf-8');
  } catch {
    content = 'Privacy Policy document not found.';
  }

  // Convert markdown-like content to simple HTML elements
  const lines = content.split('\n');
  const elements: React.ReactElement[] = [];
  
  lines.forEach((line, index) => {
    const trimmed = line.trim();
    
    if (trimmed.startsWith('# ')) {
      elements.push(
        <h1 key={index} className="text-3xl font-bold mt-8 mb-6">{trimmed.replace('# ', '')}</h1>
      );
    } else if (trimmed.startsWith('## ')) {
      elements.push(
        <h2 key={index} className="text-2xl font-semibold mt-8 mb-4">{trimmed.replace('## ', '')}</h2>
      );
    } else if (trimmed.startsWith('### ')) {
      elements.push(
        <h3 key={index} className="text-xl font-semibold mt-6 mb-3">{trimmed.replace('### ', '')}</h3>
      );
    } else if (trimmed.startsWith('- ')) {
      elements.push(
        <li key={index} className="ml-6 mb-1">{trimmed.replace('- ', '')}</li>
      );
    } else if (trimmed.match(/^\d+\.\s/)) {
      elements.push(
        <p key={index} className="ml-6 mb-2">{trimmed}</p>
      );
    } else if (trimmed === '') {
      elements.push(<div key={index} className="h-3" />);
    } else {
      elements.push(
        <p key={index} className="mb-4 text-[var(--muted)]">{trimmed}</p>
      );
    }
  });

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 px-4 py-24">
        <article className="max-w-3xl mx-auto">
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-4">Privacy Policy</h1>
            <p className="text-[var(--muted)]">Last updated: 2024</p>
          </div>
          <div className="prose-content">
            {elements}
          </div>
        </article>
      </main>
      <Footer />
    </div>
  );
}
