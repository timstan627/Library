import axios, { AxiosRequestConfig } from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || ''

// Request deduplication tracking
const pendingRequests = new Map<string, Promise<any>>()

function getRequestKey(config: AxiosRequestConfig): string {
    return `${config.method}:${config.url}:${JSON.stringify(config.params || {})}:${JSON.stringify(config.data || {})}`
}

export const api = axios.create({
    baseURL: `${API_URL}/api/v1`,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 30000, // 30 second timeout
})

// Request interceptor with deduplication
api.interceptors.request.use(
    (config) => {
        if (typeof window !== 'undefined') {
            const token = localStorage.getItem('access_token')
            if (token) {
                // console.log('Attaching token:', token.substring(0, 10) + '...')
                config.headers.Authorization = `Bearer ${token}`
            } else if (process.env.NODE_ENV === 'development') {
                // Expected on public pages for anonymous visitors; keep the noise out of production consoles
                console.warn('No token found in localStorage')
            }
        }
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

// Response interceptor with comprehensive error handling
api.interceptors.response.use(
    (response) => {
        // Clear from pending requests on success
        const key = getRequestKey(response.config)
        pendingRequests.delete(key)
        return response
    },
    async (error) => {
        const originalRequest = error.config
        const key = originalRequest ? getRequestKey(originalRequest) : null

        // Clear from pending requests on error
        if (key) pendingRequests.delete(key)

        // Network error detection
        if (!error.response) {
            const networkError = new Error('Network error. Please check your connection.')
                ; (networkError as any).isNetworkError = true
            return Promise.reject(networkError)
        }

        // HIGH-002: Handle 403 (access denied) - Do NOT force logout, just show error
        if (error.response?.status === 403) {
            // Simply let the caller handle the error (usually showing a permissions message)
            console.warn('Access denied (403):', error.response?.data?.detail)
            return Promise.reject(error)
        }

        // Token refresh on 401
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true

            try {
                const refreshToken = localStorage.getItem('refresh_token')
                if (refreshToken) {
                    const response = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
                        refresh_token: refreshToken,
                    })

                    const { access_token, refresh_token } = response.data
                    localStorage.setItem('access_token', access_token)
                    localStorage.setItem('refresh_token', refresh_token)

                    originalRequest.headers.Authorization = `Bearer ${access_token}`
                    return api(originalRequest)
                }
            } catch (refreshError) {
                // Refresh failed — session is dead
            }

            // Clear tokens and redirect to login
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
            if (typeof window !== 'undefined') {
                const currentPath = window.location.pathname
                // Only redirect if not already on auth pages
                if (!currentPath.startsWith('/auth/')) {
                    window.location.href = `/auth/login?returnUrl=${encodeURIComponent(currentPath)}`
                }
            }
        }

        return Promise.reject(error)
    }
)

/**
 * Make a deduplicated API request.
 * Prevents multiple identical requests from being sent simultaneously.
 */
export function deduplicatedRequest<T>(config: AxiosRequestConfig): Promise<T> {
    const key = getRequestKey(config)

    // Return existing promise if request is already pending
    if (pendingRequests.has(key)) {
        return pendingRequests.get(key)!
    }

    const promise = api.request<T>(config).finally(() => {
        pendingRequests.delete(key)
    })

    pendingRequests.set(key, promise)
    return promise as Promise<T>
}

// API helper functions
export const apiHelpers = {
    // Resources
    getResources: (params?: any) => api.get('/resources', { params }),
    getMyResources: (params?: { page?: number; size?: number }) =>
        api.get('/resources/my', { params }),
    getResource: (id: string) => api.get(`/resources/${id}`),
    getResourceBySlug: (slug: string) => api.get(`/resources/slug/${slug}`),
    uploadResource: (formData: FormData) =>
        api.post('/resources/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            timeout: 120000, // 2 minute timeout for uploads
        }),
    updateResource: (id: string, data: any) => api.put(`/resources/${id}`, data),
    deleteResource: (id: string) => api.delete(`/resources/${id}`),

    // Search
    search: (params: any) => api.get('/search', { params }),
    getFilters: () => api.get('/search/filters'),
    getFilterOptions: () => api.get('/search/filters'), // Alias for getFilters
    getPopular: (limit?: number) => api.get('/search/popular', { params: { limit } }),
    getRecent: (limit?: number) => api.get('/search/recent', { params: { limit } }),
    getCollections: () => api.get('/library/collections'),
    getCollection: (id: string) => api.get(`/library/collections/${id}`),

    // Ratings
    createRating: (resourceId: string, data: { value: number; review?: string }) =>
        api.post(`/ratings/resources/${resourceId}`, data),
    getResourceRatings: (resourceId: string, params?: any) =>
        api.get(`/ratings/resources/${resourceId}`, { params }),

    // Users
    getProfile: () => api.get('/users/me'),
    updateProfile: (data: any) => api.put('/users/me', data),
    getStorageInfo: () => api.get('/users/me/storage'),

    // Departments & Courses
    getDepartments: () => api.get('/departments'),
    getCourses: (departmentId?: string) => api.get('/courses', { params: { department_id: departmentId } }),

    // Moderation (Admin)
    getPendingModeration: (page = 1, size = 20) => api.get('/admin/moderation/pending', { params: { page, page_size: size } }),
    moderateResource: (id: string, data: { action: 'approve' | 'reject'; rejection_reason?: string }) =>
        api.post(`/admin/moderation/${id}/moderate`, data),
    getModerationHistory: (page = 1, size = 20) => api.get('/admin/moderation/history', { params: { page, page_size: size } }),
    getModerationStats: () => api.get('/admin/moderation/stats'),

    // Admin - Departments
    getDepartmentsAdmin: (page = 1, size = 50) => api.get('/admin/departments', { params: { page, page_size: size } }),
    createDepartment: (data: any) => api.post('/admin/departments', data),
    updateDepartment: (id: string, data: any) => api.put(`/admin/departments/${id}`, data),
    deleteDepartment: (id: string) => api.delete(`/admin/departments/${id}`),
    toggleDepartment: (id: string) => api.patch(`/admin/departments/${id}/toggle`),

    // Admin - Courses
    getCoursesAdmin: (departmentId?: string, page = 1, size = 50) =>
        api.get('/admin/courses', { params: { department_id: departmentId, page, page_size: size } }),
    createCourse: (data: any) => api.post('/admin/courses', data),
    updateCourse: (id: string, data: any) => api.put(`/admin/courses/${id}`, data),
    deleteCourse: (id: string) => api.delete(`/admin/courses/${id}`),

    // Admin - User Promotion
    getTrustedUsers: () => api.get('/admin/users/trusted'),
    promoteUser: (userId: string, data: { is_trusted: boolean }) =>
        api.post(`/admin/users/${userId}/promote`, data),
    getUserPromotionStatus: (userId: string) => api.get(`/admin/users/${userId}/promotion`),

    // Admin - Audit Logs
    getAuditLogs: (page = 1, size = 50) => api.get('/admin/moderation/audit-logs', { params: { page, page_size: size } }),

    // Admin - Reports
    getReportsAdmin: (reportStatus?: string, page = 1, size = 20) =>
        api.get('/admin/reports', { params: { report_status: reportStatus || undefined, page, page_size: size } }),
    resolveReport: (id: string, data: { action: 'resolved' | 'dismissed'; resolution_note?: string }) =>
        api.put(`/admin/reports/${id}`, data),

    // Catalog shelves (public discovery rows; empty list → frontend defaults)
    getCatalogShelves: () => api.get('/catalog/shelves'),

    // Admin - Catalog shelf management
    getShelvesAdmin: () => api.get('/admin/catalog/shelves'),
    createShelf: (data: { title: string; source_type: string; source_value?: string | null; item_limit?: number; position?: number; is_active?: boolean }) =>
        api.post('/admin/catalog/shelves', data),
    updateShelf: (id: string, data: { title: string; source_type: string; source_value?: string | null; item_limit?: number; position?: number; is_active?: boolean }) =>
        api.put(`/admin/catalog/shelves/${id}`, data),
    toggleShelf: (id: string) => api.patch(`/admin/catalog/shelves/${id}/toggle`),
    moveShelf: (id: string, direction: 'up' | 'down') =>
        api.patch(`/admin/catalog/shelves/${id}/move`, { direction }),
    deleteShelf: (id: string) => api.delete(`/admin/catalog/shelves/${id}`),

    // Admin - Site settings (global moderation policy)
    getModerationSetting: () => api.get('/admin/settings/moderation'),
    setModerationAutoApprove: (auto_approve_moderation: boolean) =>
        api.patch('/admin/settings/moderation', { auto_approve_moderation }),

    // Admin - Per-user moderation exemption
    setUserModerationExempt: (userId: string, moderation_exempt: boolean) =>
        api.patch(`/admin/users/${userId}/moderation-exempt`, { moderation_exempt }),
}
