import React, { useState } from 'react';
import { Lock, User, Loader2, Eye, EyeOff } from 'lucide-react';
import { login, AuthUser } from '../lib/api';

interface LoginProps {
  onLogin: (user: AuthUser) => void;
}

export function Login({ onLogin }: LoginProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  // FIX B20 (Bao_Cao_QA_Lan_3.md — Trung bình): "ô Mật khẩu chỉ có biểu
  // tượng ổ khoá, KHÔNG có nút con mắt để xem lại mật khẩu vừa gõ."
  const [showPassword, setShowPassword] = useState(false);
  const [showForgotInfo, setShowForgotInfo] = useState(false);

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
                  name="username"
                  id="login-username"
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
              <div className="flex items-center justify-between">
                <label className="block text-sm font-medium text-slate-700">Mật khẩu</label>
                {/* FIX B20: liên kết "Quên mật khẩu" — hệ thống chưa có dịch
                    vụ email/reset tự động, nên hiển thị hướng dẫn liên hệ
                    quản trị viên thay vì một liên kết chết không hoạt động. */}
                <button
                  type="button"
                  onClick={() => setShowForgotInfo((v) => !v)}
                  className="text-xs text-brand-blue hover:underline font-medium"
                >
                  Quên mật khẩu?
                </button>
              </div>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-slate-400" />
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  name="password"
                  id="login-password"
                  className="focus:ring-brand-blue focus:border-brand-blue block w-full pl-10 pr-10 sm:text-sm border-slate-300 rounded-md py-2 px-3 border outline-none"
                  placeholder="Mật khẩu"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
                {/* FIX B20: nút con mắt hiện/ẩn mật khẩu vừa gõ. */}
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
                  title={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
              {showForgotInfo && (
                <p className="mt-1.5 text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded px-2.5 py-1.5">
                  Hệ thống chưa hỗ trợ tự đặt lại mật khẩu qua email. Vui lòng liên hệ quản trị viên hệ thống của
                  đơn vị bạn để được cấp lại mật khẩu.
                </p>
              )}
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
