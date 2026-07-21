'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import type { BlogPost, BlogPostCreate, PostStatus } from '@/types';

export default function AdminBlogPage() {
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
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
  };

  const [formData, setFormData] = useState<BlogPostCreate>(emptyForm);

  useEffect(() => {
    loadPosts();
  }, []);

  const loadPosts = async () => {
    setLoading(true);
    const result = await api.getAdminBlogPosts(1, 100);
    if (result.error) setError(result.error);
    else setPosts(result.data?.posts || []);
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
    loadPosts();
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
    loadPosts();
  };

  const handleTogglePublish = async (post: BlogPost) => {
    const isPublished = post.status === 'published';
    const result = isPublished
      ? await api.unpublishPost(post.id)
      : await api.publishPost(post.id);
    if (!result.error) loadPosts();
  };

  const handleApprove = async (post: BlogPost) => {
    const result = await api.approvePost(post.id);
    if (!result.error) loadPosts();
  };

  const handleReject = async (post: BlogPost) => {
    const reason = window.prompt('Rejection reason:');
    if (!reason) return;
    const result = await api.rejectPost(post.id, reason);
    if (!result.error) loadPosts();
  };

  const generateSlug = (title: string) =>
    title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

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
          <p className="text-[var(--muted)]">Manage blog posts</p>
        </div>
        <button
          onClick={() => { setEditingPost(null); setFormData(emptyForm); setShowModal(true); }}
          className="px-6 py-3 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity"
        >
          + New Post
        </button>
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
      <div className="rounded-2xl bg-[var(--card)] border border-[var(--border)] overflow-hidden">
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

      {/* Modal */}
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
                <label className="block text-sm font-medium mb-2">Slug</label>
                <input
                  type="text"
                  value={formData.tags || ''}
                  placeholder="auto-generated-from-title"
                  className="w-full px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none opacity-60"
                  readOnly
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
    </div>
  );
}
