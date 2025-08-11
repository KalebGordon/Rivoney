import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ResumeBuilder from './components/pages/ResumeBuilder';
import ResumeGenerator from './components/pages/ResumeGenerator';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<ResumeBuilder />} />
        <Route path="/resume/generator" element={<ResumeGenerator />} />
      </Routes>
    </Router>
  );
}

export default App;