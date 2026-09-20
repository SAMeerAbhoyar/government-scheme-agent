import React, { useContext } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { Landmark, User, LogOut, Shield, Bookmark, History, Layers, Search } from 'lucide-react';

const Navbar = () => {
  const { user, logout } = useContext(AuthContext);
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path;

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-blue-600 flex items-center justify-center text-white shadow-md group-hover:scale-105 transition-transform">
            <Landmark className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-slate-900 tracking-tight text-lg block leading-tight">
              GovScheme Agent
            </span>
            <span className="text-[10px] text-slate-500 font-medium tracking-wide uppercase">
              Central & Maharashtra
            </span>
          </div>
        </Link>

        {user ? (
          <div className="flex items-center gap-2 sm:gap-4">
            <nav className="flex items-center space-x-1 sm:space-x-2 mr-2">
              <Link
                to="/"
                className={`flex items-center gap-1.5 text-xs sm:text-sm font-medium px-3 py-1.5 rounded-lg transition-colors ${isActive('/') ? 'bg-indigo-50 text-indigo-700 font-bold' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`}
              >
                <Search className="w-4 h-4" />
                <span>Discover</span>
              </Link>

              <Link
                to="/saved"
                className={`flex items-center gap-1.5 text-xs sm:text-sm font-medium px-3 py-1.5 rounded-lg transition-colors ${isActive('/saved') ? 'bg-indigo-50 text-indigo-700 font-bold' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`}
              >
                <Bookmark className="w-4 h-4" />
                <span>Saved</span>
              </Link>

              <Link
                to="/history"
                className={`flex items-center gap-1.5 text-xs sm:text-sm font-medium px-3 py-1.5 rounded-lg transition-colors ${isActive('/history') ? 'bg-indigo-50 text-indigo-700 font-bold' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`}
              >
                <History className="w-4 h-4" />
                <span>History</span>
              </Link>

              <Link
                to="/compare"
                className={`flex items-center gap-1.5 text-xs sm:text-sm font-medium px-3 py-1.5 rounded-lg transition-colors ${isActive('/compare') ? 'bg-indigo-50 text-indigo-700 font-bold' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`}
              >
                <Layers className="w-4 h-4" />
                <span>Compare</span>
              </Link>
            </nav>

            <div className="h-4 w-px bg-slate-200 hidden sm:block"></div>

            <Link
              to="/profile"
              className={`flex items-center gap-1.5 text-xs sm:text-sm font-medium px-3 py-1.5 rounded-lg transition-colors ${isActive('/profile') ? 'bg-indigo-50 text-indigo-700 font-bold' : 'text-slate-600 hover:bg-slate-50'}`}
            >
              <User className="w-4 h-4 text-slate-500" />
              <span className="hidden md:inline">Profile</span>
            </Link>

            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 text-xs sm:text-sm font-medium text-slate-600 hover:text-rose-600 transition-colors px-2 py-1.5 rounded-lg hover:bg-rose-50"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <Link
              to="/login"
              className="text-sm font-semibold text-slate-700 hover:text-indigo-600 px-4 py-2 rounded-lg transition-colors"
            >
              Sign In
            </Link>
            <Link
              to="/signup"
              className="text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-lg shadow-sm hover:shadow transition-all"
            >
              Get Started
            </Link>
          </div>
        )}
      </div>
    </header>
  );
};

export default Navbar;
