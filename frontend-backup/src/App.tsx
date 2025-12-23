import { useEffect, useState } from 'react';
import reactLogo from './assets/react.svg';
import viteLogo from '/vite.svg';
import './App.css';

function App() {
  const [count, setCount] = useState(0);
  const [health, setHealth] = useState<string | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  // Fetch the FastAPI health endpoint on component mount
  useEffect(() => {
    // Adjust the URL if the backend runs on a different host/port
    fetch('http://localhost:8000/api/v1/health')
      .then(async (response) => {
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        return response.json();
      })
      .then((data) => {
        // Assuming the health response has a `status` field
        setHealth(data.status ?? JSON.stringify(data));
        setHealthError(null);
      })
      .catch((err) => {
        setHealth(null);
        setHealthError(err.message);
      });
  }, []);

  return (
    <>
      <div>
        <a href="https://vite.dev" target="_blank">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <h1>Vite + React</h1>

      {/* Health check display */}
      <section className="health-section">
        <h2>Backend Health</h2>
        {health && <p className="health-success">Status: {health}</p>}
        {healthError && <p className="health-error">Error: {healthError}</p>}
        {!health && !healthError && <p>Loading health status...</p>}
      </section>

      <div className="card">
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
        <p>
          Edit <code>src/App.tsx</code> and save to test HMR
        </p>
      </div>
      <p className="read-the-docs">
        Click on the Vite and React logos to learn more
      </p>
    </>
  );
}

export default App;
