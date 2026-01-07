import { NextRequest, NextResponse } from 'next/server'
import { getApiBaseUrl } from '@/lib/api-base'

function getBaseUrl(request: NextRequest): string {
  // Use X-Forwarded headers from Cloudflare/proxy, or fall back to request URL
  const forwardedProto = request.headers.get('x-forwarded-proto') || 'https'
  const forwardedHost = request.headers.get('x-forwarded-host') || request.headers.get('host')

  if (forwardedHost) {
    return `${forwardedProto}://${forwardedHost}`
  }

  // Fallback to environment variable
  return process.env.NEXT_PUBLIC_APP_URL || 'https://autoban.learnai.cz'
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const code = searchParams.get('code')
  const state = searchParams.get('state')
  const error = searchParams.get('error')
  const baseUrl = getBaseUrl(request)

  // Handle OAuth errors
  if (error) {
    return NextResponse.redirect(`${baseUrl}/login?error=${encodeURIComponent(error)}`)
  }

  if (!code || !state) {
    return NextResponse.redirect(`${baseUrl}/login?error=missing_code`)
  }

  try {
    // Exchange code for token with backend
    const requestHost = request.headers.get('x-forwarded-host') || request.headers.get('host') || request.nextUrl.host
    const protocol = request.headers.get('x-forwarded-proto') || request.nextUrl.protocol
    const apiUrl = getApiBaseUrl({ hostname: requestHost ?? undefined, protocol: protocol ?? undefined })
    const response = await fetch(
      `${apiUrl}/api/v1/auth/callback/github?code=${code}&state=${state}`,
      { method: 'GET' }
    )

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage = errorData.detail || 'Authentication failed'
      return NextResponse.redirect(`${baseUrl}/login?error=${encodeURIComponent(errorMessage)}`)
    }

    const data = await response.json()

    // Create response with redirect to dashboard
    const redirectResponse = NextResponse.redirect(`${baseUrl}/dashboard`)

    // Determine cookie domain for cross-subdomain sharing
    const cookieHost = request.headers.get('host') || ''
    const isProduction = cookieHost.includes('learnai.cz')
    const cookieDomain = isProduction ? '.learnai.cz' : undefined

    // Set auth cookie - sameSite: 'none' required for cross-origin API requests
    redirectResponse.cookies.set('access_token', data.access_token, {
      httpOnly: true,
      secure: true,  // Required for sameSite: 'none'
      sameSite: 'none',  // Allow cross-origin requests to include cookie
      maxAge: data.expires_in,
      path: '/',
      domain: cookieDomain,
    })

    // Set user info cookie (non-httpOnly for client access)
    redirectResponse.cookies.set('user', JSON.stringify({
      id: data.user_id,
      email: data.email,
      name: data.name,
      avatar_url: data.avatar_url,
    }), {
      httpOnly: false,
      secure: true,
      sameSite: 'none',
      maxAge: data.expires_in,
      path: '/',
      domain: cookieDomain,
    })

    return redirectResponse
  } catch (error) {
    console.error('GitHub OAuth callback error:', error)
    return NextResponse.redirect(`${baseUrl}/login?error=server_error`)
  }
}
