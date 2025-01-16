import { Route, BrowserRouter, Routes } from "react-router-dom";
import Home from "./Pages/Home";
import Room from "./Pages/Room";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/:userId" element={<Home />} />
        <Route path="/room" element={<Room />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
