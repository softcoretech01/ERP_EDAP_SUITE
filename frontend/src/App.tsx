import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './layouts/MainLayout';
import { Login } from './pages/Login';
import { Chat } from './pages/Chat';
import { Dashboard } from './pages/Dashboard';
import { Connections } from './pages/Connections';
import { Configuration } from './pages/Configuration';
import { Signup } from './pages/Signup';

import { Uploads } from './pages/Uploads';

const MockPage = ({ title }: { title: string }) => (
  <div className="flex items-center justify-center h-full text-slate-400 text-xl font-medium">
    {title} Page (Coming Soon)
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Chat />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="connections" element={<Connections />} />
          <Route path="configuration" element={<Configuration />} />
          <Route path="uploads" element={<Uploads />} />
          <Route path="history" element={<MockPage title="History" />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
