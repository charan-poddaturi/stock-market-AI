import type { Metadata } from 'next'
import './globals.css'
import Sidebar from '@/components/Sidebar'
import TopBar from '@/components/TopBar'
import { Toaster } from 'react-hot-toast'

export const metadata: Metadata = {
  title: 'StockAI — AI-Powered Market Intelligence',
  description: 'Next-generation stock market analysis, prediction, and trading simulation platform powered by machine learning and deep learning.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-bg-primary text-slate-200 antialiased">
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0 ml-[220px]" style={{ marginLeft: '220px' }}>
            <TopBar />
            <main className="flex-1 overflow-y-auto p-6" style={{ paddingTop: '80px' }}>
              {children}
            </main>
          </div>
        </div>
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: '#111827',
              color: '#e2e8f0',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '12px',
            },
          }}
        />
      </body>
    </html>
  )
}
