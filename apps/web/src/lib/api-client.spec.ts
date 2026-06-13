import { apiClient, ApiError } from './api-client';

describe('apiClient', () => {
  let mockFetch: jest.Mock;

  beforeEach(() => {
    mockFetch = jest.fn();
    global.fetch = mockFetch;

    // Mock window to simulate browser environment
    global.window = {
      location: {
        href: 'http://localhost/'
      }
    } as any;
  });

  afterEach(() => {
    jest.clearAllMocks();
    delete (global as any).window;
  });

  describe('success responses', () => {
    it('should return parsed json when response is ok', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ data: 'test' })
      });

      const result = await apiClient('/test');
      expect(result).toEqual({ data: 'test' });
    });

    it('should return undefined when response status is 204', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
        json: async () => ({}) // Should not be called
      });

      const result = await apiClient('/test');
      expect(result).toBeUndefined();
    });
  });

  describe('error handling', () => {
    it('should throw ApiError with body.message if present when response is not ok', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ message: 'Invalid data provided' })
      });

      try {
        await apiClient('/test');
        fail('Should have thrown an error');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).message).toBe('Invalid data provided');
        expect((error as ApiError).status).toBe(400);
      }
    });

    it('should throw ApiError with fallback statusText when response is not ok and json parsing fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => Promise.reject(new Error('Invalid JSON'))
      });

      try {
        await apiClient('/test');
        fail('Should have thrown an error');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).message).toBe('Internal Server Error');
        expect((error as ApiError).status).toBe(500);
      }
    });

    it('should throw ApiError with fallback HTTP status when response is not ok, json is valid but missing message', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: async () => ({ error: 'something else' })
      });

      try {
        await apiClient('/test');
        fail('Should have thrown an error');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).message).toBe('HTTP 403');
        expect((error as ApiError).status).toBe(403);
      }
    });

    it('should redirect to login when response status is 401', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ message: 'Unauthorized access' })
      });

      try {
        await apiClient('/test');
        fail('Should have thrown an error');
      } catch (error) {
        expect(global.window.location.href).toBe('/login');
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).status).toBe(401);
      }
    });

    it('should not throw on 401 if window is undefined', async () => {
      // Temporarily delete window
      delete (global as any).window;

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ message: 'Unauthorized access' })
      });

      try {
        await apiClient('/test');
        fail('Should have thrown an error');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).status).toBe(401);
      }
    });
  });

  describe('url handling', () => {
    it('should use provided url if it starts with http', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({})
      });

      await apiClient('https://external.api/test');
      expect(mockFetch).toHaveBeenCalledWith('https://external.api/test', expect.any(Object));
    });

    it('should prefix with API_BASE if path does not start with http', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({})
      });

      // Based on the code, default API_BASE is http://localhost:4000/api/v1
      await apiClient('/test');
      expect(mockFetch).toHaveBeenCalledWith('http://localhost:4000/api/v1/test', expect.any(Object));
    });
  });
});
