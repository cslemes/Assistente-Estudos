import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ConfigProvider, theme } from 'antd';
import './index.css';
import App from './App.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#38bdf8',
          colorBgBase: '#0f172a',
          colorBgContainer: '#1e293b',
          colorBgElevated: '#1e293b',
          colorBorder: '#334155',
          borderRadius: 8,
          fontFamily: 'Inter, system-ui, sans-serif',
        },
        components: {
          Layout: {
            headerBg: '#1e293b',
            siderBg: '#1e293b',
            bodyBg: '#0f172a',
          },
          Menu: {
            darkItemBg: '#1e293b',
            darkSubMenuItemBg: '#0f172a',
          },
          Tabs: {
            inkBarColor: '#38bdf8',
            itemActiveColor: '#38bdf8',
            itemSelectedColor: '#38bdf8',
          },
        },
      }}
    >
      <App />
    </ConfigProvider>
  </StrictMode>,
);
