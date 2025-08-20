// src/components/Layout.jsx
import "./Styles/Layout.css";

const Layout = ({ children }) => {
  return (
    <div className="layout-container">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="header-inner">
            {/* Logo */}
            <div className="logo-section">
              <div className="logo-container">
                <h1 className="logo-title">WebAudit Pro</h1>
              </div>
            </div>

            {/* Navigation */}
            <nav className="navigation">
              <a href="#" className="nav-link">
                Dashboard
              </a>
              <a href="#" className="nav-link">
                History
              </a>
              <a href="#" className="nav-link">
                Reports
              </a>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">{children}</main>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-content">
          <div className="footer-inner">
            <p className="footer-copyright">
              © 2025 WebAudit Pro. All rights reserved.
            </p>
            <div className="footer-links">
              <a href="#" className="footer-link">
                Documentation
              </a>
              <a href="#" className="footer-link">
                Support
              </a>
              <a href="#" className="footer-link">
                Privacy
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
