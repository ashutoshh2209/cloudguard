export class ApiError extends Error {
  constructor(public status: number, public message: string, public data?: any) {
    super(message);
    this.name = 'ApiError';
  }
}

export class UnauthorizedError extends ApiError {
  constructor(message = 'Unauthorized', data?: any) {
    super(401, message, data);
    this.name = 'UnauthorizedError';
  }
}

export class ForbiddenError extends ApiError {
  constructor(message = 'Forbidden', data?: any) {
    super(403, message, data);
    this.name = 'ForbiddenError';
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');
  
  const token = localStorage.getItem('cloudguard_token');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  
  try {
    const response = await fetch(url, {
      ...options,
      headers
    });
    
    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch (e) {
        errorData = { detail: response.statusText };
      }
      
      let message = 'An API error occurred';
      if (typeof errorData?.detail === 'string') {
        message = errorData.detail;
      } else if (Array.isArray(errorData?.detail)) {
        message = errorData.detail
          .map((item: any) => (typeof item === 'string' ? item : item.msg || JSON.stringify(item)))
          .join('; ');
      } else if (typeof errorData?.message === 'string') {
        message = errorData.message;
      } else if (errorData?.detail && typeof errorData.detail === 'object') {
        message = errorData.detail.msg || JSON.stringify(errorData.detail);
      }
      
      if (response.status === 401) {
        // Clear token on 401
        localStorage.removeItem('cloudguard_token');
        throw new UnauthorizedError(message, errorData);
      } else if (response.status === 403) {
        throw new ForbiddenError(message, errorData);
      } else {
        throw new ApiError(response.status, message, errorData);
      }
    }
    
    // For 204 No Content
    if (response.status === 204) {
      return {} as T;
    }
    
    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Network errors or parsing errors
    throw new ApiError(500, error instanceof Error ? error.message : 'Unknown network error');
  }
}
