import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Eye, EyeOff, LogIn } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Toaster, toast } from 'sonner';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_novavision-finanzas/artifacts/jssdpppr_logo%20nova%20transparente.png";

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error('Por favor completa todos los campos');
      return;
    }

    setLoading(true);
    try {
      await login(email, password);
      toast.success('¡Bienvenido!');
      navigate('/dashboard');
    } catch (error) {
      const message = error.response?.data?.detail || 'Credenciales incorrectas';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      <Toaster position="top-right" richColors />
      
      {/* Left side - Image */}
      <div 
        className="hidden lg:flex lg:w-1/2 bg-cover bg-center relative"
        style={{ 
          backgroundImage: `url('https://images.unsplash.com/photo-1772557526164-db6af0e8c4eb?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA4Mzl8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMGxpZ2h0JTIwdGVhbCUyMHNvZnQlMjBnZW9tZXRyaWMlMjBiYWNrZ3JvdW5kfGVufDB8fHx8MTc3NDU4NDE3Nnww&ixlib=rb-4.1.0&q=85')` 
        }}
      >
        <div className="absolute inset-0 bg-gradient-to-br from-teal-900/80 to-teal-700/70" />
        <div className="relative z-10 flex flex-col justify-center p-12 text-white">
          <img 
            src={LOGO_URL} 
            alt="NovaVision Logo" 
            className="w-[580px] mb-8 drop-shadow-lg"
          />
          <h1 className="text-4xl font-bold mb-4 font-['Outfit']">
            Sistema de Gastos y Finanzas
          </h1>
          <p className="text-lg text-teal-100 max-w-md">
            Gestiona los gastos de tu clínica oftalmológica de manera eficiente y profesional.
          </p>
        </div>
      </div>

      {/* Right side - Login form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-slate-50">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex flex-col items-center mb-8">
            <img 
              src={LOGO_URL} 
              alt="NovaVision Logo" 
              className="w-[450px] mb-2"
            />
            <p className="text-sm text-slate-500">Sistema de Gastos y Finanzas</p>
          </div>

          <Card className="border-0 shadow-lg">
            <CardHeader className="space-y-1 pb-6">
              <CardTitle className="text-2xl font-bold text-center font-['Outfit']">
                Iniciar Sesión
              </CardTitle>
              <CardDescription className="text-center">
                Ingresa tus credenciales para acceder
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Correo Electrónico</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="tu@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="h-11"
                    data-testid="login-email-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Contraseña</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="h-11 pr-10"
                      data-testid="login-password-input"
                    />
                    <button
                      type="button"
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  className="w-full h-11 bg-teal-800 hover:bg-teal-900 text-white font-medium"
                  disabled={loading}
                  data-testid="login-submit-button"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Ingresando...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <LogIn className="w-4 h-4" />
                      Iniciar Sesión
                    </span>
                  )}
                </Button>
              </form>

              {/* Demo credentials */}
              <div className="mt-6 p-4 bg-slate-100 rounded-lg">
                <p className="text-xs font-semibold text-slate-600 mb-2">Usuarios de prueba:</p>
                <div className="space-y-1 text-xs text-slate-500">
                  <p><span className="font-medium">SuperAdmin:</span> superadmin@novavision.gt / nova2024</p>
                  <p><span className="font-medium">Admin:</span> admin@novavision.gt / admin2024</p>
                  <p><span className="font-medium">Usuario:</span> usuario@novavision.gt / user2024</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Login;
