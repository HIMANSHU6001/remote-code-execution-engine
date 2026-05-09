"use client";

import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";
import Cookies from "js-cookie";
import {
  loginApiAuthLoginPost,
  signupApiAuthSignupPost,
  socialAuthApiAuthSocialPost,
  type LoginRequest,
  type SignupRequest
} from "@/lib/api-client";
import { client } from "@/lib/api-client/client.gen";
import { auth, googleProvider, githubProvider } from "@/lib/firebase";
import { signInWithPopup, type AuthProvider as FirebaseAuthProvider } from "firebase/auth";
import { handleSocialAuthAction } from "@/app/actions/auth";

interface AuthContextType {
  token: string | null;
  isAuthenticated: boolean;
  login: (data: LoginRequest) => Promise<void>;
  signup: (data: SignupRequest) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  loginWithGithub: () => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedToken = Cookies.get("auth_token");
    if (savedToken) {
      setToken(savedToken);
      client.setConfig({
        headers: {
          Authorization: `Bearer ${savedToken}`,
        },
      });
    }
    setLoading(false);
  }, []);

  const login = async (data: LoginRequest) => {
    const response = await loginApiAuthLoginPost({ body: data });
    if (response.error) {
      throw new Error("Login failed");
    }
    const token = response.data.access_token;
    Cookies.set("auth_token", token, { expires: 7 });
    setToken(token);
    client.setConfig({
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  };

  const signup = async (data: SignupRequest) => {
    const response = await signupApiAuthSignupPost({ body: data });
    if (response.error) {
      throw new Error("Signup failed");
    }
  };

  const handleSocialLogin = async (firebaseProvider: FirebaseAuthProvider) => {
    try {
      const result = await signInWithPopup(auth, firebaseProvider);
      const user = result.user;

      if (!user.email) throw new Error("Email not found from social provider");

      const response = await handleSocialAuthAction({
        email: user.email,
        name: user.displayName || "",
        provider: firebaseProvider.providerId,
        provider_account_id: user.uid,
      });

      if (response.error || !response.data) {
        throw new Error(response.error || "Social login failed on backend");
      }

      const token = response.data.access_token;
      Cookies.set("auth_token", token, { expires: 7 });
      setToken(token);
      client.setConfig({
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
    } catch (error: any) {
      console.error("Social login error:", error);
      throw error;
    }
  };

  const loginWithGoogle = () => handleSocialLogin(googleProvider);
  const loginWithGithub = () => handleSocialLogin(githubProvider);

  const logout = () => {
    Cookies.remove("auth_token");
    setToken(null);
    client.setConfig({
      headers: {
        Authorization: undefined,
      },
    });
  };

  return (
    <AuthContext.Provider value={{
      token,
      isAuthenticated: !!token,
      login,
      signup,
      loginWithGoogle,
      loginWithGithub,
      logout,
      loading
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
