// src/App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import Results from './pages/Results';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App min-h-screen bg-gray-50">
        <Routes>
          {/* Home page - main analysis form */}
          <Route path="/" element={<Home />} />
          
          {/* Results page - for viewing specific analysis results */}
          <Route path="/results/:analysisId" element={<Results />} />
          
          {/* Catch-all route - redirect to home */}
          <Route path="*" element={<Home />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;