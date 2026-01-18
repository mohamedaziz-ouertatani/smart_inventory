"use client";
import { useAuth } from "./AuthProvider";
import { useRouter } from "next/navigation";

export default function LogoutButton() {
  const { setToken } = useAuth();
  const router = useRouter();

  function handleLogout() {
    setToken(null);
    router.push("/login");
  }

  return <button onClick={handleLogout}>Logout</button>;
}
