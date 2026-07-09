import './index.css';
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';

const savedFont = localStorage.getItem('mnemonic.font');
if (savedFont) document.documentElement.style.setProperty('--app-font', savedFont);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
