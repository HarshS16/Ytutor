import { createContext, useContext, useState, useEffect } from 'react';
import { getMe, login as apiLogin, signup as apiSignup } from '../api/client';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('ytutor_token');
      if (token) {
        try {
          const userData = await getMe();
          setUser(userData);
          setIsAuthenticated(true);
        } catch (error) {
          console.error("Failed to restore session", error);
          localStorage.removeItem('ytutor_token');
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email, password) => {
    const data = await apiLogin(email, password);
    localStorage.setItem('ytutor_token', data.access_token);
    setUser(data.user);
    setIsAuthenticated(true);
    return data;
  };

  const signup = async (email, username, password) => {
    await apiSignup(email, username, password);
    // Auto-login after signup
    return await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem('ytutor_token');
    setUser(null);
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, loading, login, signup, logout }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
