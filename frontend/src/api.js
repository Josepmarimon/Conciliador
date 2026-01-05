import axios from 'axios';

// API configuration
const API_URL = import.meta.env.VITE_API_URL || 'https://conciliador-awct.onrender.com';
// const API_URL = 'http://localhost:8000'; // Local development

// Create axios instance with default config
const api = axios.create({
    baseURL: API_URL,
    timeout: 60000, // 60 seconds for file processing
});

// Token storage keys
const ACCESS_TOKEN_KEY = 'conciliador_access_token';
const REFRESH_TOKEN_KEY = 'conciliador_refresh_token';
const USER_KEY = 'conciliador_user';

// Token management functions
export const getAccessToken = () => localStorage.getItem(ACCESS_TOKEN_KEY);
export const getRefreshToken = () => localStorage.getItem(REFRESH_TOKEN_KEY);
export const getStoredUser = () => {
    const user = localStorage.getItem(USER_KEY);
    return user ? JSON.parse(user) : null;
};

export const setTokens = (accessToken, refreshToken, user) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
};

export const clearTokens = () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
};

// Request interceptor - add auth token to requests
api.interceptors.request.use(
    (config) => {
        const token = getAccessToken();
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response interceptor - handle 401 and token refresh
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        // If 401 and we haven't tried to refresh yet
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            const refreshToken = getRefreshToken();
            if (refreshToken) {
                try {
                    // Try to refresh the token
                    const response = await axios.post(`${API_URL}/auth/refresh`, {
                        refresh_token: refreshToken,
                    });

                    const { access_token, refresh_token } = response.data;
                    const user = getStoredUser();
                    setTokens(access_token, refresh_token, user);

                    // Retry the original request with new token
                    originalRequest.headers.Authorization = `Bearer ${access_token}`;
                    return api(originalRequest);
                } catch (refreshError) {
                    // Refresh failed - clear tokens and redirect to login
                    clearTokens();
                    window.location.href = '/';
                    return Promise.reject(refreshError);
                }
            }

            // No refresh token - clear and redirect
            clearTokens();
            window.location.href = '/';
        }

        return Promise.reject(error);
    }
);

// Auth API functions
export const login = async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    const { access_token, refresh_token, user } = response.data;
    setTokens(access_token, refresh_token, user);
    return response.data;
};

export const logout = () => {
    clearTokens();
};

export const getCurrentUser = async () => {
    const response = await api.get('/auth/me');
    return response.data;
};

export const changePassword = async (currentPassword, newPassword) => {
    const response = await api.put('/auth/me/password', {
        current_password: currentPassword,
        new_password: newPassword,
    });
    return response.data;
};

// Stats API (public, no auth required)
export const getStats = async () => {
    try {
        const response = await axios.get(`${API_URL}/stats`);
        return response.data;
    } catch (error) {
        console.error('Error fetching stats:', error);
        return null;
    }
};

// Reconciliation API (requires auth)
export const conciliateFile = async (file, tol, arPrefix, apPrefix, justifications = {}) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/conciliate', formData, {
        params: {
            tol: tol,
            ar_prefix: arPrefix,
            ap_prefix: apPrefix,
            justifications: JSON.stringify(justifications),
        },
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

// User management API (admin only)
export const listUsers = async () => {
    const response = await api.get('/users');
    return response.data;
};

export const createUser = async (email, password, role = 'user') => {
    const response = await api.post('/users', { email, password, role });
    return response.data;
};

export const updateUser = async (userId, data) => {
    const response = await api.put(`/users/${userId}`, data);
    return response.data;
};

export const deactivateUser = async (userId) => {
    await api.delete(`/users/${userId}`);
};

export const resetUserPassword = async (userId) => {
    const response = await api.post(`/users/${userId}/reset-password`);
    return response.data;
};

export default api;
