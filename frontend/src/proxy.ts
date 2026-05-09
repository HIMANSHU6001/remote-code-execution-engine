import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function proxy(request: NextRequest) {
  const token = request.cookies.get('auth_token');
  const isAuthPage = request.nextUrl.pathname.startsWith('/auth');
  const isVerifyPage = request.nextUrl.pathname.startsWith('/verify-email');

  if (!token && !isAuthPage && !isVerifyPage) {
    return NextResponse.redirect(new URL('/auth', request.url));
  }

  if (token && isAuthPage) {
    return NextResponse.redirect(new URL('/problems', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};
