'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import type { BlogPost, BlogPostCreate, BlogCategory } from '@/types';

export default function AdminBlogPage() {
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [categories, setCategories] = useState<BlogCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [editingPost, setEditingPost] = useState<BlogPost | null>(null);
  const [saving, setSaving] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const emptyForm: BlogPostCreate = {
    title: '',
    content: '',
    excerpt: '',
    cover_image_url: '',
    meta_description: '',
    tags: '',
    featured: false,
    category_ids: [],
  };

  const [formData, setFormData] = useState<BlogPostCreate>(emptyForm);
  const [categoryForm, setCategoryForm] = useState({ name: '', description: '', color: '#6366f1' });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    const [postsResult, catsResult] = await Promise.all([
      api.getAdminBlogPosts(1, 100),
      api.getAdminBlogCategories(),
    ]);
    if (postsResult.error) setError(postsResult.error);
    else setPosts(postsResult.data?.posts || []);
    if (catsResult.error) console.error(catsResult.error);
    else setCategories(catsResult.data?.categories || []);
    setLoading(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title || !formData.content) {
      alert('Title and content are required');
      return;
    }
    setSaving(true);
    const result = editingPost
      ? await api.updateBlogPost(editingPost.id, formData)
      : await api.createBlogPost(formData);
    if (result.error) {
      alert(result.error);
      setSaving(false);
      return;
    }
    setShowModal(false);
    setEditingPost(null);
    setFormData(emptyForm);
    loadData();
    setSaving(false);
  };

  const handleEdit = (post: BlogPost) => {
    setEditingPost(post);
    setFormData({
      title: post.title,
      content: post.content,
      excerpt: post.excerpt || '',
      cover_image_url: post.cover_image_url || '',
      meta_description: post.meta_description || '',
      tags: Array.isArray(post.tags) ? post.tags.join(', ') : (post.tags || ''),
      featured: post.featured || false,
      category_ids: post.categories?.map(c => c.id) || [],
    });
    setShowModal(true);
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Delete this post? This cannot be undone.')) return;
    const result = await api.deleteBlogPost(id);
    if (result.error) {
      alert(result.error);
      return;
    }
    loadData();
  };

  const handleTogglePublish = async (post: BlogPost) => {
    const isPublished = post.status === 'published';
    const result = isPublished
      ? await api.unpublishPost(post.id)
      : await api.publishPost(post.id);
    if (!result.error) loadData();
  };

  const handleToggleFeatured = async (post: BlogPost) => {
    const result = await api.updateBlogPost(post.id, { featured: !post.featured });
    if (!result.error) loadData();
  };

  const handleApprove = async (post: BlogPost) => {
    const result = await api.approvePost(post.id);
    if (!result.error) loadData();
  };

  const handleReject = async (post: BlogPost) => {
    const reason = window.prompt('Rejection reason:');
    if (!reason) return;
    const result = await api.rejectPost(post.id, reason);
    if (!result.error) loadData();
  };

  const handleCategorySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryForm.name) return;
    setSaving(true);
    const result = await api.createBlogCategory(categoryForm);
    if (result.error) {
      alert(result.error);
      setSaving(false);
      return;
    }
    setShowCategoryModal(false);
    setCategoryForm({ name: '', description: '', color: '#6366f1' });
    loadData();
    setSaving(false);
  };

  const handleDeleteCategory = async (id: string) => {
    if (!window.confirm('Delete this category?')) return;
    const result = await api.deleteBlogCategory(id);
    if (result.error) {
      alert(result.error);
      return;
    }
    loadData();
  };

  const formatDate = (d: string) =>
    new Date(d).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  const statusColor = (status: string) => {
    switch (status) {
      case 'published': return 'bg-green-500/20 text-green-400';
      case 'pending': return 'bg-yellow-500/20 text-yellow-400';
      case 'approved': return 'bg-blue-500/20 text-blue-400';
      case 'scheduled': return 'bg-purple-500/20 text-purple-400';
      case 'archived': return 'bg-gray-500/20 text-gray-400';
      default: return 'bg-gray-500/20 text-gray-400';
    }
  };

  const filteredPosts = statusFilter === 'all'
    ? posts
    : posts.filter(p => p.status === statusFilter);

  return (
    <div className="max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">
            Blog <span className="gradient-text">Posts</span>
          </h1>
          <p className="text-[var(--muted)]">Manage blog posts and categories</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowCategoryModal(true)}
            className="px-4 py-3 rounded-xl border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
          >
            Categories
          </button>
          <button
            onClick={() => { setEditingPost(null); setFormData(emptyForm); setShowModal(true); }}
            className="px-6 py-3 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity"
          >
            + New Post
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
        </div>
      )}

      {/* Status Filter */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {['all', 'draft', 'pending', 'approved', 'published', 'scheduled', 'archived'].map(s => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium capitalize transition-all ${
              statusFilter === s
                ? 'bg-[var(--primary)] text-black'
                : 'bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:text-[var(--foreground)]'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Posts Table */}
      <div className="rounded-2xl bg-[var(--card)] border border-[var(--border)] overflow-hidden mb-8">
        {loading ? (
          <div className="p-8 text-center text-[var(--muted)]">Loading...</div>
        ) : filteredPosts.length === 0 ? (
          <div className="p-8 text-center text-[var(--muted)]">No posts yet. Create your first post!</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  <th className="text-left p-4 font-medium text-[var(--muted)]">Title</th>
                  <th className="text-left p-4 font-medium text-[var(--muted)]">Featured</th>
                  <th className="text-left p-4 font-medium text-[var(--muted)]">Status</th>
                  <th className="text-left p-4 font-medium text-[var(--muted)]">Views</th>
                  <th className="text-left p-4 font-medium text-[var(--muted)]">Created</th>
                  <th className="text-right p-4 font-medium text-[var(--muted)]">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredPosts.map(post => (
                  <tr key={post.id} className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--card-hover)]">
                    <td className="p-4 font-medium">{post.title}</td>
                    <td className="p-4">
                      <button
                        onClick={() => handleToggleFeatured(post)}
                        className={`px-2 py-1 rounded-lg text-xs ${post.featured ? 'bg-yellow-500/20 text-yellow-400' : 'bg-gray-500/20 text-gray-400'}`}
                      >
                        {post.featured ? '★ Featured' : '☆ Not featured'}
                      </button>
                    </td>
                    <td className="p-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${statusColor(post.status)}`}>
                        {post.status}
                      </span>
                    </td>
                    <td className="p-4 text-[var(--muted)]">{post.view_count}</td>
                    <td className="p-4 text-[var(--muted)]">{formatDate(post.created_at)}</td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-2 flex-wrap">
                        {post.status === 'pending' && (
                          <>
                            <button onClick={() => handleApprove(post)} className="px-3 py-1 rounded-lg bg-blue-500/20 text-blue-400 text-xs hover:bg-blue-500/30">Approve</button>
                            <button onClick={() => handleReject(post)} className="px-3 py-1 rounded-lg bg-red-500/20 text-red-400 text-xs hover:bg-red-500/30">Reject</button>
                          </>
                        )}
                        <button onClick={() => handleEdit(post)} className="px-3 py-1 rounded-lg bg-[var(--card-hover)] text-[var(--muted)] text-xs hover:text-[var(--foreground)]">Edit</button>
                        <button onClick={() => handleTogglePublish(post)} className={`px-3 py-1 rounded-lg text-xs ${post.status === 'published' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400'}`}>
                          {post.status === 'published' ? 'Unpublish' : 'Publish'}
                        </button>
                        <button onClick={() => handleDelete(post.id)} className="px-3 py-1 rounded-lg bg-red-500/20 text-red-400 text-xs hover:bg-red-500/30">Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Categories Panel */}
      <div className="rounded-2xl bg-[var(--card)] border border-[var(--border)] p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Categories</h2>
          <button
            onClick={() => setShowCategoryModal(true)}
            className="px-4 py-2 rounded-lg bg-[var(--primary)] text-black text-sm font-medium"
          >
            + Add Category
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {categories.map(cat => (
            <div key={cat.id} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)]">
              <span
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: cat.color || '#6366f1' }}
              />
              <span className="text-sm">{cat.name}</span>
              <span className="text-xs text-[var(--muted)]">({cat.post_count || 0})</span>
              <button
                onClick={() => handleDeleteCategory(cat.id)}
                className="text-red-400 hover:text-red-300 text-xs"
              >
                ×
              </button>
            </div>
          ))}
          {categories.length === 0 && (
            <p className="text-[var(--muted)] text-sm">No categories yet</p>
          )}
        </div>
      </div>

      {/* Post Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-[var(--card)] rounded-2xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto border border-[var(--border)]">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold">{editingPost ? 'Edit Post' : 'New Post'}</h2>
              <button onClick={() => setShowModal(false)} className="text-[var(--muted)] hover:text-white text-xl">&times;</button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Title *</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={e => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="Post title"
                  className="w-full px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Excerpt</label>
                <textarea
                  value={formData.excerpt || ''}
                  onChange={e => setFormData(prev => ({ ...prev, excerpt: e.target.value }))}
                  placeholder="Short summary for cards and meta description"
                  className="w-full px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none min-h-[80px]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Cover Image URL</label>
                <input
                  type="url"
                  value={formData.cover_image_url || ''}
                  onChange={e => setFormData(prev => ({ ...prev, cover_image_url: e.target.value }))}
                  placeholder="https://..."
                  className="w-full px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Content (Markdown) *</label>
                <textarea
                  value={formData.content}
                  onChange={e => setFormData(prev => ({ ...prev, content: e.target.value }))}
                  placeholder="Write your post in Markdown..."
                  className="w-full px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none min-h-[300px]"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">SEO Meta Description</label>
                <textarea
                  value={formData.meta_description || ''}
                  onChange={e => setFormData(prev => ({ ...prev, meta_description: e.target.value }))}
                  placeholder="Custom meta description for search engines"
                  className="w-full px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none min-h-[60px]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Tags (comma-separated)</label>
                <input
                  type="text"
                  value={formData.tags || ''}
                  onChange={e => setFormData(prev => ({ ...prev, tags: e.target.value }))}
                  placeholder="proxy, guide, tutorial"
                  className="w-full px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Categories</label>
                <div className="flex flex-wrap gap-2">
                  {categories.map(cat => (
                    <label key={cat.id} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] cursor-pointer hover:bg-[var(--card-hover)]/80">
                      <input
                        type="checkbox"
                        checked={formData.category_ids?.includes(cat.id) || false}
                        onChange={e => {
                          const ids = formData.category_ids || [];
                          if (e.target.checked) {
                            setFormData(prev => ({ ...prev, category_ids: [...ids, cat.id] }));
                          } else {
                            setFormData(prev => ({ ...prev, category_ids: ids.filter(id => id !== cat.id) }));
                          }
                        }}
                        className="rounded"
                      />
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: cat.color || '#6366f1' }}
                      />
                      <span className="text-sm">{cat.name}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="featured"
                  checked={formData.featured || false}
                  onChange={e => setFormData(prev => ({ ...prev, featured: e.target.checked }))}
                  className="rounded"
                />
                <label htmlFor="featured" className="text-sm font-medium">Mark as featured</label>
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 py-3 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {saving ? 'Saving...' : editingPost ? 'Update Post' : 'Create Post'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-6 py-3 rounded-xl border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)]"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Category Modal */}
      {showCategoryModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-[var(--card)] rounded-2xl p-6 w-full max-w-md border border-[var(--border)]">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold">Add Category</h2>
              <button onClick={() => setShowCategoryModal(false)} className="text-[var(--muted)] hover:text-white text-xl">&times;</button>
            </div>
            <form onSubmit={handleCategorySubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Name *</label>
                <input
                  type="text"
                  value={categoryForm.name}
                  onChange={e => setCategoryForm(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Category name"
                  className="w-full px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Description</label>
                <textarea
                  value={categoryForm.description}
                  onChange={e => setCategoryForm(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Optional description"
                  className="w-full px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none min-h-[60px]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Color</label>
                <div className="flex gap-2">
                  <input
                    type="color"
                    value={categoryForm.color}
                    onChange={e => setCategoryForm(prev => ({ ...prev, color: e.target.value }))}
                    className="w-10 h-10 rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={categoryForm.color}
                    onChange={e => setCategoryForm(prev => ({ ...prev, color: e.target.value }))}
                    placeholder="#6366f1"
                    className="flex-1 px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                  />
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 py-3 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {saving ? 'Creating...' : 'Create Category'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowCategoryModal(false)}
                  className="px-6 py-3 rounded-xl border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)]"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
