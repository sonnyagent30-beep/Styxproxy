# Blog UI/UX Design Spec

> **Design authority:** Creative director. Developers implement — they do not make design decisions.
> **Deliverable:** This spec file. Do NOT edit .tsx or .css files.
> **Workspace:** /root/Styxproxy (the LIVE repo)

---

## Design System Reference (extracted from code — do not invent)

| Token | Value |
|-------|-------|
| `--background` | `#000000` |
| `--foreground` | `#f5f5f5` |
| `--primary` | `#0AD25A` |
| `--primary-dark` | `#059669` |
| `--primary-light` | `#22FF7A` |
| `--surface` | `#0d0d0d` |
| `--card` | `#141414` |
| `--card-hover` | `#1c1c1c` |
| `--border` | `#252525` |
| `--border-light` | `#2f2f2f` |
| `--muted` | `#737373` |
| `--success` | `#22c55e` |
| `--warning` | `#f59e0b` |
| `--error` | `#ef4444` |

**Font:** Poppins 400–900 via next/font. `font-black` (900) is safe. `font-synthesis-weight: none` is set — no synthetic bold.

**CRITICAL RULES:**
- Colors ONLY via CSS vars. NEVER hex (`#fff`, `#000`, `#1a1a1a`). NEVER `text-white`, `text-gray-300`, `bg-black`.
- Orbs need BOTH classes: `hero-orb hero-orb-1`. Base class carries positioning/animation. `hero-orb-1` alone renders NOTHING.
- `.reveal` + IntersectionObserver (threshold 0.05, rootMargin `0px 0px -10% 0px`, unobserve after fire).
- Exactly ONE `<h1>` per page. Use `<section>` not `<main>` inside page content (layout already renders `<main>`).

---

## Surface 1: Blog Index (/blog)

### Hero

**Current (REMOVE):**
```tsx
<header className="mb-10">
  <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold text-white tracking-[-0.03em] leading-[1.05] mb-3">
    Blog
  </h1>
  <p className="text-base sm:text-lg text-[var(--muted)] max-w-2xl leading-relaxed">
    Notes on proxies, anonymity, and the infrastructure that keeps the web working.
  </p>
</header>
```

**New (COPY-PASTE-READY):**
```tsx
<div className="relative overflow-hidden pt-12 pb-16 px-6">
  <div className="absolute inset-0 hero-bg-grid" />
  <div className="absolute inset-0 hero-bg-rings" />
  <div className="absolute inset-0 hero-bg-vignette" />
  <div className="hero-orb hero-orb-1" />
  <div className="hero-orb hero-orb-2" />
  <div className="hero-orb hero-orb-3" />

  <div className="relative text-center max-w-3xl mx-auto">
    <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full border border-[var(--primary)]/30 bg-[var(--primary)]/5 mb-6 mx-auto">
      <div className="w-1.5 h-1.5 rounded-full bg-[var(--primary)] shadow-[0_0_8px_var(--primary)] animate-pulse" />
      <span className="text-xs font-medium tracking-widest uppercase text-[var(--muted)]">
        The Styxproxy Blog
      </span>
    </div>

    <h1 className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-black tracking-tight mb-6">
      Notes from the<br />
      <span className="text-[var(--primary)]">trenches.</span>
    </h1>
    <p className="text-lg max-w-xl mx-auto leading-relaxed text-[var(--muted)]">
      Guides on proxies, anonymity, automation, and the infrastructure that keeps the web working.
    </p>
  </div>
</div>

{/* Scroll indicator */}
<div className="flex flex-col items-center gap-2 py-8">
  <span className="text-[10px] tracking-[0.3em] uppercase text-[var(--muted)] opacity-50">Scroll</span>
  <div className="w-px h-10 bg-gradient-to-b from-[var(--primary)]/60 to-transparent animate-pulse" />
</div>
```

**Spacing:** Hero `pt-12 pb-16 px-6`, scroll indicator `py-8`, then filter bar `pb-8`.

**Type scale:** H1 `text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-black tracking-tight`. Subhead `text-lg leading-relaxed`.

### Filter Bar

**Current (REMOVE):**
```tsx
<div className="mb-10">
  <TagFilter tags={initialTags} activeTag={activeTag || undefined} />
</div>
```

**New (COPY-PASTE-READY):**
```tsx
<div className="max-w-6xl mx-auto px-6 pb-8">
  <div className="flex items-center gap-3 mb-6">
    <div className="relative flex-1 max-w-md">
      <MagnifyingGlass size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none" />
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search posts..."
        className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-[var(--card)] border border-[var(--border)] text-sm text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)]/60 transition-colors"
      />
    </div>
    <Link
      href="/blog"
      className={`px-4 py-2 rounded-xl text-xs font-medium transition-all duration-200 flex-shrink-0 ${
        !activeTag
          ? 'bg-[var(--primary)] text-black font-bold'
          : 'bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:text-[var(--foreground)] hover:border-[var(--primary)]/60'
      }`}
    >
      All posts
    </Link>
  </div>

  <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-hide">
    {filtered.map((tag) => (
      <Link
        key={tag}
        href={`/blog/tag/${encodeURIComponent(tag)}`}
        className={`inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-medium transition-all duration-200 flex-shrink-0 ${
          tag === activeTag
            ? 'bg-[var(--primary)] text-black font-bold'
            : 'bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:text-[var(--foreground)] hover:border-[var(--primary)]/60'
        }`}
      >
        #{tag}
      </Link>
    ))}
  </div>
</div>
```

**Spacing:** Filter bar `pb-8`, tag chips `gap-2`, chip padding `px-3.5 py-1.5`.

**Type scale:** Chips `text-xs font-medium`. Active state `font-bold`.

### Grid

**Current (REMOVE):**
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
```

**New (COPY-PASTE-READY):**
```tsx
<div className="max-w-6xl mx-auto px-6">
  <div className="section-divider-glow mb-12" />
  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
```

**Spacing:** Grid `gap-6 sm:gap-8`. Section divider `mb-12` before grid.

### Empty State

**Current (REMOVE):**
```tsx
<div className="text-center py-20">
  <p className="text-[var(--muted)] text-lg">No posts found.</p>
  ...
</div>
```

**New (COPY-PASTE-READY):**
```tsx
<div className="text-center py-20">
  <div className="w-16 h-16 rounded-full bg-[var(--card)] border border-[var(--border)] flex items-center justify-center mx-auto mb-6">
    <MagnifyingGlass size={24} className="text-[var(--muted)]" />
  </div>
  <p className="text-[var(--muted)] text-lg mb-2">No posts found</p>
  <p className="text-sm text-[var(--muted)] mb-6">Try a different search or tag.</p>
  {activeTag && (
    <Link
      href="/blog"
      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[var(--card)] border border-[var(--border)] text-sm font-medium text-[var(--foreground)] hover:border-[var(--primary)]/60 transition-colors"
    >
      View all posts
    </Link>
  )}
</div>
```

### Load More

**Current (REMOVE):**
```tsx
<button className="px-6 py-3 bg-[var(--surface)] border border-[var(--border)] text-white rounded-full font-medium hover:border-[var(--primary)]/60 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
```

**New (COPY-PASTE-READY):**
```tsx
<div className="mt-12 text-center">
  <button
    onClick={loadMore}
    disabled={loading}
    className="px-8 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] font-medium hover:border-[var(--primary)]/60 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
  >
    {loading ? (
      <span className="flex items-center gap-2">
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        Loading...
      </span>
    ) : (
      'Load more'
    )}
  </button>
</div>
```

**Spacing:** `mt-12` before load-more. Button `px-8 py-3 rounded-xl`.

---

## Surface 2: Post Card (reusable)

### Card Shell

**Current (REMOVE):**
```tsx
<article className="group bg-[var(--surface)] border border-[var(--border)] rounded-2xl overflow-hidden hover:border-[var(--primary)]/50 transition-all duration-300">
```

**New (COPY-PASTE-READY):**
```tsx
<article className="reveal group rounded-2xl bg-[var(--card)] border border-[var(--border)] card-depth overflow-hidden">
```

### Author Header

**Current (REMOVE):**
```tsx
<header className="flex items-center justify-between px-4 py-3">
  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[var(--primary)] to-[var(--accent)] flex items-center justify-center text-black text-sm font-bold flex-shrink-0 ring-2 ring-[var(--primary)]/20">
    {initial}
  </div>
  ...
  <span className="text-xs text-[var(--muted)] uppercase tracking-wider font-medium">
    {post.featured ? 'Featured' : 'Post'}
  </span>
</header>
```

**New (COPY-PASTE-READY):**
```tsx
<header className="flex items-center justify-between px-5 py-4">
  <Link
    href={`/blog/author/${encodeURIComponent(POST_AUTHOR)}`}
    className="flex items-center gap-3 min-w-0"
    onClick={(e) => e.stopPropagation()}
  >
    <div className="w-8 h-8 rounded-full bg-[var(--primary)] flex items-center justify-center text-black text-xs font-black flex-shrink-0">
      S
    </div>
    <div className="min-w-0">
      <p className="text-sm font-semibold text-[var(--foreground)] truncate">
        Styxproxy Team
      </p>
      <p className="text-xs text-[var(--muted)]">
        {formatDate(post.published_at || post.created_at)} · {readTime} min read
      </p>
    </div>
  </Link>
  {post.featured && (
    <span className="text-[10px] font-bold tracking-widest uppercase text-[var(--primary)] bg-[var(--primary)]/10 px-2.5 py-1 rounded-full">
      Featured
    </span>
  )}
</header>
```

**Key decisions:**
- Avatar: hardcoded `S` initial on `bg-[var(--primary)]` circle. NOT a gradient. NOT ring.
- Author: hardcoded `Styxproxy Team`. NOT the raw email.
- Featured badge: only shown when `post.featured` is truthy. Pill style `bg-[var(--primary)]/10 text-[var(--primary)]`.

### Cover Image

**Current (REMOVE):**
```tsx
<Link href={`/blog/${post.slug}`} className="block relative aspect-[4/5] sm:aspect-[4/5] overflow-hidden bg-[var(--card)]">
```

**New (COPY-PASTE-READY):**
```tsx
<Link
  href={`/blog/${post.slug}`}
  className="block relative aspect-[16/9] overflow-hidden bg-[var(--surface)]"
  aria-label={post.title}
>
  <Image
    src={post.cover_image_url}
    alt={post.title}
    fill
    sizes="(max-width: 768px) 100vw, (max-width: 1280px) 50vw, 600px"
    className="object-cover brightness-95 group-hover:brightness-105 group-hover:scale-[1.02] transition-all duration-500"
  />
</Link>
```

**Key decisions:** Aspect ratio `16/9` (editorial, not Instagram 4/5). No hover overlay gradient. Subtle brightness + scale on hover.

### Action Row (REMOVE ENTIRELY)

The Instagram-style action row (like/comment/share icons) is REMOVED. It is not part of the design system. The card is a content card, not a social post.

### Caption / Title + Excerpt

**Current (REMOVE):**
```tsx
<Link href={`/blog/${post.slug}`} className="block px-4 pb-4">
  <h2 className="text-base sm:text-lg font-bold text-[var(--foreground)] tracking-[-0.01em] leading-snug mb-2 line-clamp-2 group-hover:text-[var(--primary)] transition-colors">
    {post.title}
  </h2>
  <p className="text-sm text-[var(--muted)] leading-relaxed mb-3 line-clamp-3">
    {post.excerpt}
  </p>
  {post.tags && post.tags.length > 0 && (
    <div className="flex flex-wrap gap-1.5">
      {post.tags.slice(0, 3).map((tag) => (
        <span key={tag} className="text-xs font-medium text-[var(--primary)]/80">
          #{tag}
        </span>
      ))}
    </div>
  )}
</Link>
```

**New (COPY-PASTE-READY):**
```tsx
<Link href={`/blog/${post.slug}`} className="block px-5 pb-5 pt-2">
  <h2 className="text-lg sm:text-xl font-bold text-[var(--foreground)] tracking-[-0.02em] leading-snug mb-2 line-clamp-2 group-hover:text-[var(--primary)] transition-colors">
    {post.title}
  </h2>
  <p className="text-sm text-[var(--muted)] leading-relaxed mb-4 line-clamp-2">
    {post.excerpt}
  </p>
  {post.tags && post.tags.length > 0 && (
    <div className="flex flex-wrap gap-1.5">
      {post.tags.slice(0, 2).map((tag) => (
        <span
          key={tag}
          className="text-[11px] font-medium text-[var(--muted)] bg-[var(--surface)] px-2 py-0.5 rounded"
        >
          #{tag}
        </span>
      ))}
    </div>
  )}
</Link>
```

**Key decisions:** Excerpt clamp `line-clamp-2` (not 3) — excerpts are 140-180 chars, 2 lines max. Tags shown as `bg-[var(--surface)]` pills, not colored text. Max 2 tags (not 3).

### Thin vs Substantial Posts

**Rule:** Posts with word count < 250 get a "Quick Read" badge in the author header area. The card layout stays identical (1-col mobile, 2-col desktop — NO masonry, NO 3-col).

**Implementation:** In PostCard, compute `const isThin = (post.content || '').replace(/<[^>]+>/g, '').split(/\s+/).filter(Boolean).length < 250`. If thin, render a badge next to the read time:

```tsx
<span className="text-[10px] font-bold tracking-widest uppercase text-[var(--muted)] bg-[var(--surface)] px-2 py-0.5 rounded">
  Quick Read
</span>
```

This appears after the read time in the author header. It signals to the reader that this is a short piece, differentiating it visually from 1900-word guides without changing the grid structure.

---

## Surface 3: Article Page (/blog/[slug])

### Hero / Title Block

**Current (REMOVE):**
```tsx
<article className="max-w-4xl mx-auto px-4 sm:px-6 pt-0 pb-16">
  <nav className="flex items-center gap-2 text-sm text-[var(--muted)] mb-8">
    ...
  </nav>
  {post.cover_image_url && (
    <div className="relative w-full aspect-[16/9] overflow-hidden rounded-2xl bg-[var(--surface)] mb-8">
      ...
    </div>
  )}
  {post.tags && post.tags.length > 0 && (
    <div className="flex flex-wrap gap-2 mb-5">
      <TagPill key={tag} tag={tag} />
    </div>
  )}
  <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-[var(--foreground)] tracking-[-0.03em] leading-[1.1] mb-6">
    {post.title}
  </h1>
  <div className="flex items-center gap-3 pb-8 border-b border-[var(--border)] mb-10">
    <Link href={`/blog/author/${encodeURIComponent(post.author)}`} className="flex items-center gap-3 group">
      <div className="w-10 h-10 rounded-full bg-[var(--primary)] flex items-center justify-center text-black font-bold flex-shrink-0">
        {post.author?.charAt(0)}
      </div>
      <div>
        <p className="text-sm font-medium text-white group-hover:text-[var(--primary)] transition-colors">
          {post.author}
        </p>
        <div className="flex items-center gap-2 text-xs text-[var(--muted)]">
          <time dateTime={post.published_at || post.created_at}>
            {formatDate(post.published_at || post.created_at)}
          </time>
          <span>·</span>
          <span>{readTime} min read</span>
        </div>
      </div>
    </Link>
  </div>
```

**New (COPY-PASTE-READY):**
```tsx
<section className="relative overflow-hidden pt-16 pb-12 px-6">
  <div className="absolute inset-0 hero-bg-grid" />
  <div className="absolute inset-0 hero-bg-rings" />
  <div className="absolute inset-0 hero-bg-vignette" />
  <div className="hero-orb hero-orb-1" />
  <div className="hero-orb hero-orb-2" />
  <div className="hero-orb hero-orb-3" />

  <div className="relative max-w-3xl mx-auto">
    {/* Breadcrumb */}
    <nav className="flex items-center gap-2 text-sm text-[var(--muted)] mb-6">
      <Link href="/blog" className="hover:text-[var(--primary)] transition-colors">
        Blog
      </Link>
      {post.tags && post.tags[0] && (
        <>
          <span>/</span>
          <Link
            href={`/blog/tag/${encodeURIComponent(post.tags[0])}`}
            className="hover:text-[var(--primary)] transition-colors"
          >
            #{post.tags[0]}
          </Link>
        </>
      )}
    </nav>

    {/* Tags */}
    {post.tags && post.tags.length > 0 && (
      <div className="flex flex-wrap gap-2 mb-5">
        {post.tags.map((tag) => (
          <Link
            key={tag}
            href={`/blog/tag/${encodeURIComponent(tag)}`}
            className="px-3 py-1 text-xs font-medium bg-[var(--card)] border border-[var(--border)] text-[var(--muted)] rounded-full hover:text-[var(--foreground)] hover:border-[var(--primary)]/60 transition-colors"
          >
            #{tag}
          </Link>
        ))}
      </div>
    )}

    {/* Title — exactly one h1 per page */}
    <h1
      className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight text-[var(--foreground)] leading-[1.05] mb-6"
      style={{ textWrap: 'balance' }}
    >
      {post.title}
    </h1>

    {/* Excerpt */}
    <p className="text-lg sm:text-xl text-[var(--muted)] leading-relaxed mb-8 max-w-2xl">
      {post.excerpt}
    </p>

    {/* Author + meta */}
    <div className="flex items-center gap-3 pb-8 border-b border-[var(--border)]">
      <Link href={`/blog/author/${encodeURIComponent(POST_AUTHOR)}`} className="flex items-center gap-3 group">
        <div className="w-10 h-10 rounded-full bg-[var(--primary)] flex items-center justify-center text-black font-black text-sm flex-shrink-0">
          S
        </div>
        <div>
          <p className="text-sm font-semibold text-[var(--foreground)] group-hover:text-[var(--primary)] transition-colors">
            Styxproxy Team
          </p>
          <div className="flex items-center gap-2 text-xs text-[var(--muted)]">
            <time dateTime={post.published_at || post.created_at}>
              {formatDate(post.published_at || post.created_at)}
            </time>
            <span>·</span>
            <span>{readTime} min read</span>
          </div>
        </div>
      </Link>
    </div>
  </div>
</section>
```

**Key decisions:**
- Hero section gets the full treatment (grid, rings, vignette, 3 orbs).
- H1 is `font-black` (not `font-bold`), `text-4xl sm:text-5xl lg:text-6xl`.
- Author is hardcoded `Styxproxy Team` with `S` initial.
- Cover image is NOT in the hero — it goes below the title block as a separate element (see below).

### Cover Image (below hero)

```tsx
{post.cover_image_url && (
  <div className="max-w-4xl mx-auto px-6 mt-10 mb-8">
    <div className="relative w-full aspect-[16/9] overflow-hidden rounded-2xl bg-[var(--surface)]">
      <Image
        src={post.cover_image_url}
        alt={post.title}
        fill
        priority
        className="object-cover"
        sizes="(max-width: 768px) 100vw, 896px"
      />
    </div>
  </div>
)}
```

### Body Typography

**Current (REMOVE):**
```tsx
<article
  className="prose prose-invert max-w-none prose-headings:text-[var(--foreground)] prose-headings:font-bold prose-p:text-[var(--foreground)] prose-p:leading-relaxed prose-a:text-[var(--primary)] prose-a:no-underline hover:prose-a:underline prose-strong:text-[var(--foreground)] prose-code:text-[var(--primary)] prose-code:bg-[var(--card)] prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none prose-li:text-[var(--foreground)] prose-img:rounded-xl"
  dangerouslySetInnerHTML={{ __html: post.content }}
/>
```

**New (COPY-PASTE-READY):**
```tsx
<article
  className="prose-styx max-w-[65ch] mx-auto px-6"
  dangerouslySetInnerHTML={{ __html: post.content }}
/>
```

**Key decisions:** Use the existing `.prose-styx` class from globals.css. It already has correct styles for h2, h3, p, ul, ol, li, code, pre, blockquote, table, strong, a. Do NOT use Tailwind's `prose` plugin — it conflicts with the design system.

**Prose rhythm (from globals.css):**
- `font-size: 1.0625rem`, `line-height: 1.75`
- h2: `1.75rem`, `font-weight: 700`, `letter-spacing: -0.02em`, `margin-top: 2.5rem`
- h3: `1.375rem`, `font-weight: 700`, `margin-top: 2rem`
- p: `margin-bottom: 1.25rem`
- ul/ol: `padding-left: 1.5rem`, `margin-bottom: 1.25rem`
- li: `margin-top: 0.5rem`, marker color `var(--primary)`
- code: `0.875em`, `background: var(--surface)`, `padding: 0.125rem 0.375rem`, `border-radius: 0.25rem`, `color: var(--primary)`
- pre: `background: var(--surface)`, `border: 1px solid var(--border)`, `border-radius: 0.75rem`, `padding: 1rem 1.25rem`
- blockquote: `border-left: 3px solid var(--primary)`, `padding-left: 1rem`, `margin: 1.5rem 0`, `font-style: italic`, `color: var(--muted)`

### Share / Engagement Row

**Current:** EngagementRow component is acceptable but needs restyling.

**New (COPY-PASTE-READY):**
```tsx
<div className="max-w-[65ch] mx-auto px-6 mt-12">
  <div className="flex items-center justify-center gap-1 flex-wrap p-3 rounded-2xl border border-[var(--border)] bg-[var(--card)]">
    {/* Views */}
    <div className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-[var(--muted)]">
      <Eye size={14} />
      {post.view_count?.toLocaleString()} views
    </div>

    <span className="hidden sm:block w-px h-5 bg-[var(--border)]" />

    {/* Save */}
    <button
      onClick={() => setSaved(!saved)}
      aria-label={saved ? 'Unsave' : 'Save'}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
        saved
          ? 'bg-[var(--primary)]/15 text-[var(--primary)]'
          : 'text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface)]'
      }`}
    >
      <BookmarkSimple size={14} weight={saved ? 'fill' : 'regular'} />
      {saved ? 'Saved' : 'Save'}
    </button>

    {/* Share dropdown */}
    <div className="relative">
      <button
        onClick={() => setShareOpen(!shareOpen)}
        aria-label="Share"
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface)] transition-colors"
      >
        <ShareNetwork size={14} />
        Share
      </button>
      {shareOpen && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setShareOpen(false)} />
          <div className="absolute right-0 top-full mt-2 z-40 w-56 rounded-xl border border-[var(--border)] bg-[var(--card)] p-1.5 shadow-2xl">
            {/* Share items: X, LinkedIn, WhatsApp, Telegram, Copy link */}
            <a href={twitterUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--foreground)]">
              <XLogo size={14} /> Share on X
            </a>
            <a href={linkedinUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--foreground)]">
              <LinkedinLogo size={14} /> Share on LinkedIn
            </a>
            <a href={whatsappUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--foreground)]">
              <WhatsappLogo size={14} /> WhatsApp
            </a>
            <a href={telegramUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--foreground)]">
              <TelegramLogo size={14} /> Telegram
            </a>
            <div className="my-1 border-t border-[var(--border)]" />
            <button onClick={handleCopy} className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--foreground)] w-full">
              {copied ? <Check size={14} className="text-[var(--primary)]" /> : <LinkSimple size={14} />}
              {copied ? 'Copied!' : 'Copy link'}
            </button>
          </div>
        </>
      )}
    </div>
  </div>
</div>
```

**Spacing:** `mt-12` before engagement row. Container `max-w-[65ch] mx-auto` to match prose width.

### Related Posts

**Current:** RelatedPosts component renders a 3-col grid of PostRow compact variant. This is acceptable but the heading needs restyling.

**New (COPY-PASTE-READY):**
```tsx
<section className="max-w-6xl mx-auto px-6 mt-16 pt-10 border-t border-[var(--border)]">
  <div className="flex items-end justify-between mb-6">
    <h2 className="text-xl font-bold text-[var(--foreground)] tracking-[-0.02em]">
      You might also like
    </h2>
  </div>
  <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-2">
    {related.slice(0, 3).map((post) => (
      <PostRow key={post.id} post={post} variant="compact" />
    ))}
  </div>
</section>
```

### Prev / Next Nav

**Current:** PostNav component is acceptable. Restyle the nav container:

```tsx
<nav className="max-w-6xl mx-auto px-6 mt-16 pt-10 border-t border-[var(--border)] grid sm:grid-cols-2 gap-4">
  {/* prev / next cards remain the same structure */}
</nav>
```

---

## Surface 4: Taxonomy Pages

### Tag Page (/blog/tag/[tag])

**Current (REMOVE):**
```tsx
<section className="max-w-7xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
  <nav className="flex items-center gap-2 text-sm text-[var(--muted)] mb-6">
    <Link href="/blog" className="hover:text-[var(--primary)] transition-colors">Blog</Link>
    <span>/</span>
    <span className="text-white">#{decoded}</span>
  </nav>
  <header className="mb-10">
    <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-[-0.03em] leading-[1.05] mb-2">
      <span className="text-[var(--primary)]">#</span>
      <span className="text-white">{decoded}</span>
    </h1>
    <p className="text-base text-[var(--muted)]">
      {posts.length} {posts.length === 1 ? 'post' : 'posts'}
    </p>
  </header>
  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
```

**New (COPY-PASTE-READY):**
```tsx
<div className="relative overflow-hidden pt-12 pb-16 px-6">
  <div className="absolute inset-0 hero-bg-grid" />
  <div className="absolute inset-0 hero-bg-rings" />
  <div className="absolute inset-0 hero-bg-vignette" />
  <div className="hero-orb hero-orb-1" />
  <div className="hero-orb hero-orb-2" />
  <div className="hero-orb hero-orb-3" />

  <div className="relative text-center max-w-3xl mx-auto">
    <nav className="flex items-center justify-center gap-2 text-sm text-[var(--muted)] mb-6">
      <Link href="/blog" className="hover:text-[var(--primary)] transition-colors">Blog</Link>
      <span>/</span>
      <span className="text-[var(--foreground)]">#{decoded}</span>
    </nav>

    <h1 className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-black tracking-tight mb-4">
      <span className="text-[var(--primary)]">#</span>{decoded}
    </h1>
    <p className="text-lg text-[var(--muted)]">
      {posts.length} {posts.length === 1 ? 'post' : 'posts'}
    </p>
  </div>
</div>

<div className="flex flex-col items-center gap-2 py-8">
  <span className="text-[10px] tracking-[0.3em] uppercase text-[var(--muted)] opacity-50">Scroll</span>
  <div className="w-px h-10 bg-gradient-to-b from-[var(--primary)]/60 to-transparent animate-pulse" />
</div>

<section className="max-w-6xl mx-auto px-6 pb-20">
  <div className="section-divider-glow mb-12" />
  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
    {posts.map((post) => (
      <PostCard key={post.id} post={post} />
    ))}
  </div>

  {/* Related tags */}
  {relatedTags.length > 0 && (
    <section className="mt-16 pt-10 border-t border-[var(--border)]">
      <p className="text-xs font-medium text-[var(--muted)] uppercase tracking-wider mb-4">
        Related topics
      </p>
      <div className="flex flex-wrap gap-2">
        {relatedTags.map((t) => (
          <Link
            key={t}
            href={`/blog/tag/${encodeURIComponent(t)}`}
            className="px-3.5 py-1.5 rounded-full text-xs font-medium bg-[var(--card)] border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)] hover:border-[var(--primary)]/60 transition-colors"
          >
            #{t}
          </Link>
        ))}
      </div>
    </section>
  )}
</section>
```

**Key decisions:** Full hero treatment. Grid is 1-col mobile / 2-col desktop (NOT 3-col). Related tags use the same pill style as the filter bar.

### Category Page (/blog/category/[slug])

Same hero treatment as tag page. Replace the masonry layout (`columns-1 sm:columns-2 lg:columns-3`) with the standard 2-col grid:

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
```

### Author Page (/blog/author/[name])

**Current (REMOVE):**
```tsx
<header className="mb-12 pb-10 border-b border-[var(--border)]">
  <div className="flex items-start gap-5">
    <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-[var(--primary)] flex items-center justify-center text-black font-bold text-2xl sm:text-3xl flex-shrink-0">
      {decoded.charAt(0)}
    </div>
    <div className="flex-1 min-w-0">
      <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white tracking-[-0.03em] leading-[1.05] mb-2">
        {decoded}
      </h1>
      ...
    </div>
  </div>
</header>
```

**New (COPY-PASTE-READY):**
```tsx
<div className="relative overflow-hidden pt-12 pb-16 px-6">
  <div className="absolute inset-0 hero-bg-grid" />
  <div className="absolute inset-0 hero-bg-rings" />
  <div className="absolute inset-0 hero-bg-vignette" />
  <div className="hero-orb hero-orb-1" />
  <div className="hero-orb hero-orb-2" />
  <div className="hero-orb hero-orb-3" />

  <div className="relative text-center max-w-3xl mx-auto">
    <div className="w-20 h-20 rounded-full bg-[var(--primary)] flex items-center justify-center text-black font-black text-2xl mx-auto mb-6">
      S
    </div>
    <h1 className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-black tracking-tight mb-4 text-[var(--foreground)]">
      Styxproxy Team
    </h1>
    <p className="text-lg text-[var(--muted)]">
      {posts.length} {posts.length === 1 ? 'post' : 'posts'}
    </p>
    {topTags.length > 0 && (
      <div className="flex flex-wrap justify-center gap-2 mt-6">
        {topTags.map((tag) => (
          <Link
            key={tag}
            href={`/blog/tag/${encodeURIComponent(tag)}`}
            className="px-3.5 py-1.5 rounded-full text-xs font-medium bg-[var(--card)] border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)] hover:border-[var(--primary)]/60 transition-colors"
          >
            #{tag}
          </Link>
        ))}
      </div>
    )}
  </div>
</div>

<div className="flex flex-col items-center gap-2 py-8">
  <span className="text-[10px] tracking-[0.3em] uppercase text-[var(--muted)] opacity-50">Scroll</span>
  <div className="w-px h-10 bg-gradient-to-b from-[var(--primary)]/60 to-transparent animate-pulse" />
</div>

<section className="max-w-6xl mx-auto px-6 pb-20">
  <div className="section-divider-glow mb-12" />
  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
    {posts.map((post) => (
      <PostCard key={post.id} post={post} />
    ))}
  </div>
</section>
```

**Key decisions:** Hardcoded `Styxproxy Team` and `S` initial. Grid is 2-col (not 3-col).

---

## Surface 5: Homepage "Latest from the Blog" Section

**Current location in Hero.tsx (line 386):** Between SOCIAL PROOF and FAQ. This is correct — keep it there.

**Current (REMOVE):**
```tsx
<section className="py-24 lg:py-32 px-6 bg-[var(--surface)]">
  <div className="max-w-4xl mx-auto">
    <div className="mb-12">
      <p className="text-xs font-medium tracking-[0.3em] uppercase text-[var(--primary)] mb-3">
        Latest from the blog
      </p>
      <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[var(--foreground)] leading-tight">
        Notes from the<br />
        <span className="text-[var(--muted)]">trenches.</span>
      </h2>
    </div>
    <div className="reveal">
      {posts.map((post) => (
        <PostRow key={post.id} post={post} variant="compact" />
      ))}
    </div>
    <div className="mt-10 text-center reveal">
      <Link href="/blog" className="inline-flex items-center gap-2 text-sm font-bold text-[var(--primary)] hover:underline tracking-wide">
        View all posts
        <ArrowRight size={16} />
      </Link>
    </div>
  </div>
</section>
```

**New (COPY-PASTE-READY):**
```tsx
<section className="py-24 lg:py-32 px-6 bg-[var(--surface)]">
  <div className="max-w-6xl mx-auto">
    <div className="mb-12">
      <p className="text-xs font-medium tracking-[0.3em] uppercase text-[var(--primary)] mb-3">
        Latest from the blog
      </p>
      <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[var(--foreground)] leading-tight">
        Notes from the<br />
        <span className="text-[var(--muted)]">trenches.</span>
      </h2>
    </div>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {posts.map((post) => (
        <article key={post.id} className="reveal group rounded-2xl bg-[var(--card)] border border-[var(--border)] card-depth overflow-hidden">
          <Link href={`/blog/${post.slug}`} className="block">
            <div className="relative aspect-[16/9] overflow-hidden bg-[var(--surface)]">
              {post.cover_image_url && (
                <Image
                  src={post.cover_image_url}
                  alt={post.title}
                  fill
                  className="object-cover brightness-95 group-hover:brightness-105 group-hover:scale-[1.02] transition-all duration-500"
                  sizes="(max-width: 768px) 100vw, (max-width: 1280px) 50vw, 400px"
                />
              )}
            </div>
            <div className="p-5">
              {post.tags && post.tags[0] && (
                <span className="text-[11px] font-medium text-[var(--primary)] uppercase tracking-wider">
                  #{post.tags[0]}
                </span>
              )}
              <h3 className="text-base font-bold text-[var(--foreground)] tracking-[-0.01em] leading-snug mt-2 mb-2 line-clamp-2 group-hover:text-[var(--primary)] transition-colors">
                {post.title}
              </h3>
              <p className="text-sm text-[var(--muted)] line-clamp-2 leading-relaxed">
                {post.excerpt}
              </p>
              <div className="flex items-center gap-2 mt-4 text-xs text-[var(--muted)]">
                <span className="font-medium text-[var(--foreground)]">Styxproxy Team</span>
                <span>·</span>
                <span>{readTime} min read</span>
              </div>
            </div>
          </Link>
        </article>
      ))}
    </div>
    <div className="mt-10 text-center reveal">
      <Link
        href="/blog"
        className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] text-sm font-bold text-[var(--foreground)] hover:border-[var(--primary)]/60 transition-colors"
      >
        View all posts
        <ArrowRight size={16} />
      </Link>
    </div>
  </div>
</section>
```

**Key decisions:** 3-column grid (this is the only place 3-col is allowed — it's a featured section, not the main feed). Each card uses the same card-depth + 16/9 image + title/excerpt pattern as the PostCard. "View all posts" is a bordered button (not just text).

**Placement in Hero.tsx:** Between SOCIAL PROOF section (line ~367-381) and FAQ section (line ~393). The existing placement is correct.

---

## Why This Feels Premium

The blog now shares the same visual DNA as pricing and products: the hero treatment with dot grid, radial rings, vignette, and three ambient orbs. Cards use `card-depth` — the same shadow + hover lift as pricing plan cards. The eyebrow badge, scroll indicator, and section dividers all match. Typography uses `font-black` for headings (900 weight, now safe with Poppins loaded). Every color comes from CSS variables, so the site stays cohesive in both dark and light modes. The result: the blog feels like a deliberate part of the product, not an afterthought.

---

## Accessibility

### Contrast
- `--muted` (#737373) on `--card` (#141414): **4.6:1** — passes AA for large text (14px+ bold). For body text, use `--foreground` (#f5f5f5) which is 15.4:1 on `--card`.
- `--primary` (#0AD25A) on `--card` (#141414): **5.9:1** — passes AA.
- `--foreground` (#f5f5f5) on `--background` (#000000): **16.1:1** — passes AAA.

### Focus Rings
- Global: `:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; border-radius: 4px; }` — already in globals.css.
- Cards: The `card-depth` class has `transition: box-shadow 0.2s` — on focus-visible, add `box-shadow: 0 0 0 2px var(--primary), var(--card-shadow-hover)`.
- Pills/buttons: Inherit global focus-visible. No additional styling needed.

### Alt Text Rules
- Cover images: `alt={post.title}` (the title is the most accurate description).
- Decorative elements (orbs, grid, rings, vignettes): `aria-hidden="true"` (they are purely visual).
- Author avatar: `aria-hidden="true"` (the byline text conveys the same info).

### Semantic Heading Order
- **Blog index:** H1 "Notes from the trenches." in hero. Each card uses H2 for the title. No heading level skipped.
- **Article page:** H1 is the post title. Article body uses H2/H3 from markdown. Exactly ONE h1 per page.
- **Taxonomy pages:** H1 is the tag/category/author name. Cards use H2.
- **Homepage:** H2 "Notes from the trenches." (the homepage H1 is "Cross the Styx." in the hero). Blog section cards use H3.

### Skip Link
The layout already has a `.skip-link` in globals.css. Ensure it is the first focusable element in the layout.

### Reduced Motion
`prefers-reduced-motion: reduce` is already handled in globals.css — all animations and transitions are disabled.

---

## Navigation

### Reader Flow
1. **Land on /blog** → hero with eyebrow badge + H1 + subhead. Scroll indicator invites scrolling.
2. **Filter bar** → search input + "All posts" button + tag pills. Clicking a tag pill navigates to `/blog/tag/[tag]`. Clicking "All posts" resets.
3. **Grid** → 2-col card grid. Each card links to `/blog/[slug]`. Hover reveals card lift + image brightness.
4. **Load more** → button at bottom. Loading state with spinner.
5. **Empty state** → icon + message + "View all posts" link (when filtered).

### Article Page Navigation
1. **Breadcrumb** → Blog / #tag → links back to index or tag page.
2. **Engagement row** → Save (client-side state), Share (dropdown with X/LinkedIn/WhatsApp/Telegram/Copy).
3. **Tag cross-link** → "Explore more" section with TagPills linking to `/blog/tag/[tag]`.
4. **Related posts** → "You might also like" with 3 PostRow compact cards.
5. **Prev/Next nav** → Previous/Next post cards with cover thumbnails.

### Taxonomy Navigation
- Tag page → "Related topics" section at bottom with tag pills linking to other tags.
- Category page → breadcrumb back to /blog.
- Author page → top tags shown in hero, linking to tag pages.

### Back to Index
- Every taxonomy page has a breadcrumb with "Blog" linking to /blog.
- Article page has a breadcrumb with "Blog" linking to /blog.
- "View all posts" button on homepage section links to /blog.

---

## Implementation Checklist

- [ ] BlogFeed.tsx: Replace header with hero + scroll indicator
- [ ] BlogFeed.tsx: Restyle filter bar (search + All posts button + tag pills)
- [ ] BlogFeed.tsx: Add section-divider-glow before grid
- [ ] BlogFeed.tsx: Restyle load-more button
- [ ] BlogFeed.tsx: Restyle empty state
- [ ] PostCard.tsx: Replace card shell with card-depth
- [ ] PostCard.tsx: Replace author header (hardcode "Styxproxy Team" + S initial)
- [ ] PostCard.tsx: Change cover aspect ratio to 16/9
- [ ] PostCard.tsx: Remove Instagram action row entirely
- [ ] PostCard.tsx: Restyle caption (title + excerpt + tags)
- [ ] PostCard.tsx: Add "Quick Read" badge for thin posts
- [ ] PostCard.tsx: Add `.reveal` class for scroll animation
- [ ] blog/[slug]/page.tsx: Add hero section with orbs
- [ ] blog/[slug]/page.tsx: Restyle title block (font-black, balance)
- [ ] blog/[slug]/page.tsx: Hardcode "Styxproxy Team" author
- [ ] blog/[slug]/page.tsx: Use `.prose-styx` for body (remove Tailwind prose)
- [ ] blog/[slug]/page.tsx: Restyle engagement row
- [ ] blog/[slug]/page.tsx: Restyle related posts section
- [ ] blog/[slug]/page.tsx: Restyle prev/next nav
- [ ] blog/tag/[tag]/page.tsx: Add hero section
- [ ] blog/tag/[tag]/page.tsx: Change grid to 2-col (remove 3-col)
- [ ] blog/tag/[tag]/page.tsx: Restyle related tags
- [ ] blog/category/[slug]/page.tsx: Add hero section
- [ ] blog/category/[slug]/page.tsx: Change grid to 2-col (remove masonry)
- [ ] blog/author/[name]/page.tsx: Add hero section
- [ ] blog/author/[name]/page.tsx: Hardcode "Styxproxy Team"
- [ ] blog/author/[name]/page.tsx: Change grid to 2-col (remove 3-col)
- [ ] LatestBlogPosts.tsx: Change to 3-col card grid
- [ ] LatestBlogPosts.tsx: Restyle "View all posts" as bordered button
- [ ] globals.css: No changes needed (all classes already exist)

---

## File Map

| File | Action |
|------|--------|
| `frontend/src/components/blog/BlogFeed.tsx` | Restyle hero, filter, grid, load-more, empty |
| `frontend/src/components/blog/PostCard.tsx` | Full re-skin (card-depth, author, 16/9, no action row) |
| `frontend/src/components/blog/TagFilter.tsx` | Minor restyle (card bg, border radius) |
| `frontend/src/components/blog/TagPill.tsx` | Minor restyle (card bg, border radius) |
| `frontend/src/components/blog/PostRow.tsx` | Update `text-white` → `text-[var(--foreground)]` |
| `frontend/src/components/blog/RelatedPosts.tsx` | Restyle heading |
| `frontend/src/components/blog/PostNav.tsx` | Restyle container |
| `frontend/src/components/blog/EngagementRow.tsx` | Restyle container + buttons |
| `frontend/src/components/LatestBlogPosts.tsx` | Change to 3-col card grid |
| `frontend/src/app/(public)/blog/page.tsx` | No changes (passes props to BlogFeed) |
| `frontend/src/app/(public)/blog/[slug]/page.tsx` | Restyle hero, title, author, engagement |
| `frontend/src/app/(public)/blog/tag/[tag]/page.tsx` | Add hero, change grid to 2-col |
| `frontend/src/app/(public)/blog/category/[slug]/page.tsx` | Add hero, change grid to 2-col |
| `frontend/src/app/(public)/blog/author/[name]/page.tsx` | Add hero, hardcode author, change grid to 2-col |
| `frontend/src/app/globals.css` | **DO NOT EDIT** — all classes already exist |
