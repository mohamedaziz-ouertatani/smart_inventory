"use client";
import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";

type AuthContextType = {
  token: string | null;
  setToken: (token: string | null) => void;
};

const AuthContext = createContext<AuthContextType>({
  token: null,
  setToken: () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);

  // On initial load, try to get token from localStorage
  useEffect(() => {
    setToken(localStorage.getItem("token"));
  }, []);

  // Keep token in sync with localStorage
  useEffect(() => {
    if (token) localStorage.setItem("token", token);
    else localStorage.removeItem("token");
  }, [token]);

  return (
    <AuthContext.Provider value={{ token, setToken }}>
      {children}
    </AuthContext.Provider>
  );
}
