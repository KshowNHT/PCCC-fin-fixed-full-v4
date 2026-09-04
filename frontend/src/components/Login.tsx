import React, { useState } from 'react';
import { Lock, User, Loader2 } from 'lucide-react';
import { login, AuthUser } from '../lib/api';

interface LoginProps {
  onLogin: (user: AuthUser) => void;
}

export function Login({ onLogin }: LoginProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      const user = await login(username, password);
      onLogin(user);
    } catch (err: any) {
      setError(err.message || 'Tài khoản hoặc mật khẩu không chính xác.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
            <div className="h-16 w-16 bg-brand-blue rounded-xl flex items-center justify-center text-white font-bold text-2xl shadow-lg">
                AI
            </div>
        </div>
        <h2 className="mt-6 text-center text-3xl font-extrabold text-slate-900">
          Đăng nhập hệ thống
        </h2>
        <p className="mt-2 text-center text-sm text-slate-600">
          Chatbot AI Tư vấn Phòng Cháy Chữa Cháy
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10 border border-slate-200">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div>
              <label className="block text-sm font-medium text-slate-700">Tài khoản</label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <User className="h-5 w-5 text-slate-400" />
                </div>
                <input
                  type="text"
                  className="focus:ring-brand-blue focus:border-brand-blue block w-full pl-10 sm:text-sm border-slate-300 rounded-md py-2 px-3 border outline-none"
                  placeholder="Tên đăng nhập"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700">Mật khẩu</label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-slate-400" />
                </div>
                <input
                  type="password"
                  className="focus:ring-brand-blue focus:border-brand-blue block w-full pl-10 sm:text-sm border-slate-300 rounded-md py-2 px-3 border outline-none"
                  placeholder="Mật khẩu"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </div>
            </div>

            {error && (
              <div className="text-red-500 text-sm text-center font-medium bg-red-50 py-2 rounded">
                {error}
              </div>
            )}

            <div>
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors disabled:opacity-60"
              >
                {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                Đăng nhập
              </button>
            </div>
          </form>

          <div className="mt-6 text-center text-xs text-slate-500">
             Tài khoản do quản trị viên hệ thống cấp. Liên hệ admin nếu chưa có tài khoản.
          </div>
        </div>
      </div>
    </div>
  );
}
