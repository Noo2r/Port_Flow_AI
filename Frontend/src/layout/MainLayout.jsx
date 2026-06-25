import Sidebar from '../components/Sidebar'

export default function MainLayout({ children }) {
  return (
    <div className="flex h-screen overflow-hidden" style={{ background: '#050a14' }}>
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        {children}
      </div>
    </div>
  )
}
