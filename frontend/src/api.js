import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'X-Tenant-Slug': 'breathe-demo' },
});

export const importAPI = {
  uploadFile: (source, file) => {
    const form = new FormData();
    form.append('source', source);
    form.append('file', file);
    return api.post('/imports/', form, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  getImports: () => api.get('/imports/'),
  getImportRecords: (id) => api.get(`/imports/${id}/records/`),
  generateSample: (source) => api.post('/generate-sample/', { source }),
};

export const recordAPI = {
  getRecords: (params = {}) => api.get('/records/', { params }),
  getRecord: (id) => api.get(`/records/${id}/`),
  approve: (id, notes = '') => api.post(`/records/${id}/approve/`, { notes }),
  reject: (id, notes = '') => api.post(`/records/${id}/reject/`, { notes }),
  flag: (id, notes = '') => api.post(`/records/${id}/flag/`, { notes }),
  bulkApprove: (ids) => api.post('/records/bulk_approve/', { ids }),
  lockApproved: () => api.post('/records/lock_approved/'),
};

export const dashboardAPI = {
  getStats: () => api.get('/dashboard/stats/'),
};

export const tenantAPI = {
  list: () => api.get('/tenants/'),
};

export default api;
