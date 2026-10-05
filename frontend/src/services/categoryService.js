import { apiRequest } from './api.js';

export const fetchCategories = () => apiRequest('/categories');
export const createCategory = (name) => apiRequest('/categories', { method: 'POST', data: { name } });
export const createSubcategory = (categoryId, name) =>
  apiRequest(`/categories/${categoryId}/subcategories`, { method: 'POST', data: { name } });
