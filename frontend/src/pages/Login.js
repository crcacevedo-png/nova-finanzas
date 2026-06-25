import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Eye, EyeOff } from 'lucide-react';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_novavision-finanzas/artifacts/qvzbrum6_logo%20nova%20transparente.png";

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(username, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al iniciar sesión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 login-gradient relative overflow-hidden">
      {/* Decorative blobs */}
      <div 
        className="glass-blob"
        style={{
          width: '300px',
          height: '300px',
          background: '#9FE1CB',
          opacity: 0.3,
          top: '-50px',
          right: '-50px',
          filter: 'blur(80px)'
        }}
      />
      <div 
        className="glass-blob"
        style={{
          width: '200px',
          height: '200px',
          background: '#7BADE2',
          opacity: 0.2,
          bottom: '50px',
          left: '-30px',
          filter: 'blur(60px)'
        }}
      />
      <div 
        className="glass-blob"
        style={{
          width: '150px',
          height: '150px',
          background: '#7DD8C0',
          opacity: 0.25,
          top: '40%',
          left: '10%',
          filter: 'blur(50px)'
        }}
      />

      {/* Login Card */}
      <div 
        className="glass-card w-full max-w-[420px] p-12 animate-fade-in relative z-10"
        data-testid="login-card"
      >
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <img 
            src={LOGO_URL}
            alt="NovaVision"
            className="w-60 h-auto"
            data-testid="login-logo"
          />
        </div>

        {/* Subtitle */}
        <p className="text-center text-sm text-[#5A7A72] mb-8 tracking-wide">
          Gestión Hospitalaria
        </p>

        {/* Error Message */}
        {error && (
          <div className="glass-error mb-6 animate-fade-in" data-testid="login-error">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Username Field */}
          <div className="space-y-2">
            <label htmlFor="username" className="glass-label block">
              Usuario
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Ingresa tu usuario"
              className="glass-input w-full"
              required
              autoComplete="username"
              data-testid="login-username-input"
            />
          </div>

          {/* Password Field */}
          <div className="space-y-2">
            <label htmlFor="password" className="glass-label block">
              Contraseña
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Ingresa tu contraseña"
                className="glass-input w-full pr-10"
                required
                autoComplete="current-password"
                data-testid="login-password-input"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#94B0A8] hover:text-[#5A7A72] transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className="glass-btn mt-6"
            disabled={loading}
            data-testid="login-submit-button"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Ingresando...
              </span>
            ) : (
              'Iniciar sesión'
            )}
          </button>
        </form>

        {/* Footer */}
        <p className="text-center text-[11px] text-[#94B0A8] mt-8">
          © 2026 NovaVision
        </p>
      </div>
    </div>
  );
};

export default Login;
