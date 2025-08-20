import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Results from "./pages/Results";

function App() {
  return (
    <Router>
      <div>
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
