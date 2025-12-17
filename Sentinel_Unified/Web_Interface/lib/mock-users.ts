// Shared mock user storage across API routes
// In production, replace with actual database

export const mockUsers: { [key: string]: { id: string; name: string; email: string; password: string } } = {}
