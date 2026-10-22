import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import '@fortune-sheet/react/dist/index.css';
import './style.css';
import './ribbon.css';
createRoot(document.getElementById('root')).render(<App />);
