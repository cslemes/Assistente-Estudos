import { BrowserRouter, Route, Routes } from 'react-router-dom';
import Home from './pages/Home';
import Player from './pages/Player';
import Resources from './pages/Resources';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/lesson/:id" element={<Player />} />
        <Route path="/lesson/:id/resources" element={<Resources />} />
      </Routes>
    </BrowserRouter>
  );
}
