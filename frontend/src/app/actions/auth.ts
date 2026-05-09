"use server";

import { SignJWT } from "jose";
import { type SocialAuthRequest, type SocialAuthResponse } from "@/lib/api-client";

export async function handleSocialAuthAction(data: SocialAuthRequest): Promise<{ data?: SocialAuthResponse; error?: string }> {
  try {
    const s2sSecret = process.env.S2S_JWT_SECRET;
    const apiUrl = process.env.INTERNAL_API_URL;

    if (!s2sSecret) {
      console.error("S2S_JWT_SECRET is not defined in environment variables");
      return { error: "Server configuration error" };
    }

    const secret = new TextEncoder().encode(s2sSecret);

    // Generate S2S Token
    const s2sToken = await new SignJWT({
      email: data.email,
      provider: data.provider,
    })
      .setProtectedHeader({ alg: "HS256" })
      .setIssuedAt()
      .setIssuer("nextjs-auth")
      .setAudience("fastapi-social")
      .setExpirationTime("1m") // Very short lived
      .setJti(crypto.randomUUID())
      .sign(secret);

    // Call Backend
    const response = await fetch(`${apiUrl}/api/auth/social`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${s2sToken}`,
        "Accept": "application/json",
      },
      body: JSON.stringify(data),
    });

    const result = await response.json();

    if (!response.ok) {
      console.error("Backend social auth failed:", result);
      return { error: result.detail || "Authentication failed" };
    }

    return { data: result as SocialAuthResponse };
  } catch (error: any) {
    console.error("Server Action Error:", error);
    return { error: error.message || "An unexpected error occurred" };
  }
}
