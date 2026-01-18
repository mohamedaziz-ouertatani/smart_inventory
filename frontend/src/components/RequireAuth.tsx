"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./AuthProvider";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!token) {
      router.replace("/login");
    }
  }, [token, router]);

  if (!token) return null; // You could show a spinner here
  return <>{children}</>;
}
