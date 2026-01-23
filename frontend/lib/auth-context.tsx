'use client'

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '@/lib/api'

interface User {
    id: string
    email: string
    display_name?: string
    role: string
    is_trusted?: boolean
    mfa_enabled: boolean
    storage_quota_bytes: number
    storage_used_bytes: number
}

interface AuthContextType {
    user: User | null
    isAuthenticated: boolean
    isLoading: boolean
    login: (email: string, password: string, mfaCode?: string) => Promise<void>
    register: (email: string, password: string, displayName?: string) => Promise<void>
    logout: () => void
    refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        // Check for stored token on mount
        const token = localStorage.getItem('access_token')
        if (token) {
            refreshUser().finally(() => setIsLoading(false))
        } else {
            setIsLoading(false)
        }
    }, [])

    const login = async (email: string, password: string, mfaCode?: string) => {
        try {
            const response = await api.post('/auth/login', {
                email,
                password,
                mfa_code: mfaCode,
            })

            const data = response.data

            if (data.requires_mfa) {
                throw new Error('MFA_REQUIRED')
            }

            localStorage.setItem('access_token', data.access_token)
            localStorage.setItem('refresh_token', data.refresh_token)

            await refreshUser()
        } catch (error: any) {
            // Format error message properly
            if (error.message === 'MFA_REQUIRED') {
                throw error
            }

            // Extract error message from API response
            let detail = error.response?.data?.detail

            // Handle FastAPI validation errors (arrays or objects)
            if (typeof detail === 'object' && detail !== null) {
                if (Array.isArray(detail)) {
                    // Multiple validation errors
                    detail = detail.map((err: any) => err.msg || JSON.stringify(err)).join(', ')
                } else if (detail.msg) {
                    // Single validation error object
                    detail = detail.msg
                } else {
                    // Generic object
                    detail = 'Invalid credentials'
                }
            }

            const message = detail || error.message || 'Login failed'
            const newError = new Error(message)
            // Preserve response with string detail for component
            if (error.response) {
                (newError as any).response = { data: { detail: message } }
            }
            throw newError
        }
    }

    const register = async (email: string, password: string, displayName?: string) => {
        try {
            await api.post('/auth/register', {
                email,
                password,
                display_name: displayName,
            })
        } catch (error: any) {
            // Extract error message from API response
            let detail = error.response?.data?.detail

            // Handle FastAPI validation errors (arrays or objects)
            if (typeof detail === 'object' && detail !== null) {
                if (Array.isArray(detail)) {
                    // Multiple validation errors
                    detail = detail.map((err: any) => err.msg || JSON.stringify(err)).join(', ')
                } else if (detail.msg) {
                    // Single validation error object
                    detail = detail.msg
                } else {
                    // Generic object - convert to string
                    detail = JSON.stringify(detail)
                }
            }

            const message = detail || error.message || 'Registration failed'
            throw new Error(message)
        }
    }

    const logout = async () => {
        // CRITICAL: Tell backend to invalidate the session
        try {
            await api.post('/auth/logout')
        } catch (e) {
            // Continue with local logout even if API fails
            console.error('Logout API call failed:', e)
        }
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        setUser(null)
    }

    const refreshUser = async () => {
        try {
            const response = await api.get('/auth/me')
            setUser(response.data)
        } catch (error) {
            logout()
        }
    }

    // HIGH-001: Multi-tab logout sync
    useEffect(() => {
        const handleStorageChange = (e: StorageEvent) => {
            if (e.key === 'access_token' && !e.newValue) {
                // Token was removed in another tab
                setUser(null)
            }
            if (e.key === 'access_token' && e.newValue && !user) {
                // Token was added in another tab
                refreshUser()
            }
        }
        window.addEventListener('storage', handleStorageChange)
        return () => window.removeEventListener('storage', handleStorageChange)
    }, [user])

    return (
        <AuthContext.Provider
            value={{
                user,
                isAuthenticated: !!user,
                isLoading,
                login,
                register,
                logout,
                refreshUser,
            }}
        >
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}
