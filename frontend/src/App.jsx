import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import Workspace from './pages/Workspace';
import './index.css';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-dark-400 grid-bg relative">
        <div className="noise-overlay" />
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/playlist/:id" element={<Workspace />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
