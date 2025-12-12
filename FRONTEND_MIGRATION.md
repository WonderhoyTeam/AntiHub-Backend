# Frontend OIDC Authentication Migration Guide

## Overview
Migration guide for integrating with the new OIDC authentication system.

**Benefits of New OIDC Endpoints:**
- Universal API across all providers (Linux.do, GitHub, PocketID)
- Consistent response format
- Easier to add new OAuth providers
- Better error handling and standardization

**Backward Compatibility:**
- Old endpoints still work but are deprecated
- Recommended to migrate within next release cycle

## Quick Start

### Available Providers
Query `/api/auth/oidc/providers` to get current list:
- `linux_do` - Linux.do community authentication
- `github` - GitHub OAuth
- `pocketid` - Self-hosted OIDC with passkey support

### API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/oidc/providers` | GET | List all available providers |
| `/api/auth/oidc/{provider}/login` | GET | Initiate OAuth login |
| `/api/auth/oidc/{provider}/callback` | POST | Handle OAuth callback |

## Migration Path

### ❌ Before (Deprecated)
```typescript
// Linux.do - Provider-specific endpoint
const response = await fetch('/api/auth/sso/initiate');

// GitHub - Different endpoint structure
const response = await fetch('/api/auth/github/login');
```

### ✅ After (Recommended)
```typescript
// Universal endpoint for ALL providers
const response = await fetch(`/api/auth/oidc/${provider}/login`);
```

## React + TypeScript Implementation

### 1. Type Definitions
```typescript
// types/auth.ts
export interface OIDCProvider {
  id: string;
  name: string;
  type: string;
  enabled: boolean;
  supports_refresh: boolean;
  description: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: {
    id: number;
    username: string;
    avatar_url?: string;
    trust_level: number;
    is_active: boolean;
  };
}

export interface AuthState {
  provider: string;
  state: string;
  timestamp: number;
}
```

### 2. Auth Service Hook
```typescript
// hooks/useOIDCAuth.ts
import { useState, useEffect } from 'react';

export function useOIDCAuth() {
  const [providers, setProviders] = useState<OIDCProvider[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch available providers
  useEffect(() => {
    fetchProviders();
  }, []);

  const fetchProviders = async () => {
    try {
      const res = await fetch('/api/auth/oidc/providers');
      const data = await res.json();
      setProviders(data.providers);
    } catch (err) {
      console.error('Failed to fetch providers:', err);
    }
  };

  const initiateLogin = async (providerId: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/auth/oidc/${providerId}/login`);
      const { authorization_url, state } = await response.json();

      // Store state for callback verification
      const authState: AuthState = {
        provider: providerId,
        state,
        timestamp: Date.now()
      };
      sessionStorage.setItem('oauth_state', JSON.stringify(authState));

      // Redirect to provider
      window.location.href = authorization_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
      setLoading(false);
    }
  };

  const handleCallback = async (code: string, state: string): Promise<LoginResponse> => {
    setLoading(true);
    setError(null);

    try {
      // Verify state
      const storedState = sessionStorage.getItem('oauth_state');
      if (!storedState) throw new Error('No OAuth state found');

      const authState: AuthState = JSON.parse(storedState);
      if (authState.state !== state) throw new Error('State mismatch');

      // Exchange code for tokens
      const response = await fetch(`/api/auth/oidc/${authState.provider}/callback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, state })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Authentication failed');
      }

      const loginData: LoginResponse = await response.json();

      // Store tokens
      localStorage.setItem('access_token', loginData.access_token);
      localStorage.setItem('refresh_token', loginData.refresh_token);

      // Clear OAuth state
      sessionStorage.removeItem('oauth_state');

      return loginData;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Callback failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return {
    providers,
    loading,
    error,
    initiateLogin,
    handleCallback
  };
}
```

### 3. Login Component
```typescript
// components/Login.tsx
import React from 'react';
import { useOIDCAuth } from '../hooks/useOIDCAuth';

export function Login() {
  const { providers, loading, error, initiateLogin } = useOIDCAuth();

  return (
    <div className="login-container">
      <h1>Sign In</h1>

      {error && <div className="error">{error}</div>}

      <div className="providers">
        {providers.map(provider => (
          <button
            key={provider.id}
            onClick={() => initiateLogin(provider.id)}
            disabled={!provider.enabled || loading}
            className="provider-button"
          >
            Sign in with {provider.name}
          </button>
        ))}
      </div>
    </div>
  );
}
```

### 4. Callback Handler Component
```typescript
// components/OAuthCallback.tsx
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOIDCAuth } from '../hooks/useOIDCAuth';

export function OAuthCallback() {
  const navigate = useNavigate();
  const { handleCallback } = useOIDCAuth();
  const [status, setStatus] = useState('Processing...');

  useEffect(() => {
    const processCallback = async () => {
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      const state = params.get('state');

      if (!code || !state) {
        setStatus('Error: Missing parameters');
        return;
      }

      try {
        const loginData = await handleCallback(code, state);
        setStatus('Success! Redirecting...');

        // Redirect to dashboard or home
        setTimeout(() => navigate('/dashboard'), 1000);
      } catch (err) {
        setStatus(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
      }
    };

    processCallback();
  }, []);

  return (
    <div className="callback-container">
      <h2>Authenticating...</h2>
      <p>{status}</p>
    </div>
  );
}
```

### 5. Protected Route Setup
```typescript
// components/ProtectedRoute.tsx
import React from 'react';
import { Navigate } from 'react-router-dom';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const accessToken = localStorage.getItem('access_token');

  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
```

### 6. Router Configuration
```typescript
// App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Login } from './components/Login';
import { OAuthCallback } from './components/OAuthCallback';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Dashboard } from './components/Dashboard';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/auth/callback" element={<OAuthCallback />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `State mismatch` | CSRF protection failed | Don't refresh during OAuth flow |
| `Unsupported provider` | Invalid provider ID | Check `/api/auth/oidc/providers` |
| `Account creation disabled` | New signups blocked | Contact administrator |
| `Invalid code` | Code expired or used | Restart login flow |

### Error Handling Example
```typescript
try {
  await handleCallback(code, state);
} catch (error) {
  if (error.message.includes('State mismatch')) {
    // Clear stale state and redirect to login
    sessionStorage.removeItem('oauth_state');
    navigate('/login');
  } else if (error.message.includes('Account creation disabled')) {
    // Show maintenance message
    setError('New account creation is temporarily disabled');
  } else {
    // Generic error handling
    setError('Authentication failed. Please try again.');
  }
}
```

## Testing Checklist

### Development
- [ ] Test login with each provider
- [ ] Verify state parameter validation
- [ ] Test error scenarios (network failure, invalid code)
- [ ] Test token refresh flow
- [ ] Verify logout clears all tokens

### Production
- [ ] Configure correct redirect URIs in OAuth provider settings
- [ ] Use HTTPS for all callback URLs
- [ ] Set up proper CORS configuration
- [ ] Implement token refresh before expiry
- [ ] Add analytics tracking for auth events

## Security Best Practices

1. **Always validate state parameter** - Prevents CSRF attacks
2. **Use sessionStorage for OAuth state** - Cleared on tab close
3. **Use localStorage for tokens** - Persistent across sessions
4. **Implement token refresh** - Before access_token expiry
5. **Clear tokens on logout** - Remove from localStorage
6. **Use HTTPS in production** - OAuth requires secure redirect URIs

## Migration Checklist

- [ ] Update login component to use `/api/auth/oidc/{provider}/login`
- [ ] Update callback handler to use `/api/auth/oidc/{provider}/callback`
- [ ] Implement state parameter validation
- [ ] Add error handling for new error cases
- [ ] Test with all supported providers
- [ ] Update environment variables for callback URLs
- [ ] Deploy frontend changes
- [ ] Monitor for any authentication errors
- [ ] Remove deprecated endpoint usage after verification

## FAQ

**Q: Will old endpoints stop working immediately?**
A: No, they're deprecated but functional. Migrate at your convenience.

**Q: Can I use multiple providers simultaneously?**
A: Yes, users can link multiple OAuth accounts to one profile (future feature).

**Q: How do I add a custom OIDC provider?**
A: Contact backend team to add provider configuration.

**Q: What about refresh tokens?**
A: Refresh tokens work the same across all providers. Use `/api/auth/refresh`.

**Q: How do I handle PocketID-specific features like passkeys?**
A: Passkey enrollment happens on PocketID's side. Your app just handles OAuth flow.
