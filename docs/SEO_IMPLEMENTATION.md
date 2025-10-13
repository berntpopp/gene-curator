# SEO Implementation Guide

**Document Version**: 1.0.0
**Last Updated**: 2025-10-13
**Issue**: #42

## Overview

Gene Curator implements comprehensive SEO metadata following 2025 best practices to enhance search engine visibility, improve social media sharing, and provide rich structured data for search engines.

## Implementation Summary

### 1. Primary Meta Tags

```html
<title>Gene Curator - Flexible Platform for Genetic Evidence Curation</title>
<meta name="description" content="...">
<meta name="keywords" content="gene curation, genetic classification, ...">
<meta name="author" content="Halbritter Lab">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://github.com/halbritter-lab/gene-curator">
```

**Purpose**: Basic SEO foundation for search engine indexing.

**Keywords Strategy**:
- **Primary**: gene curation, genetic classification, gene-disease relationships
- **Secondary**: ClinGen SOP, GenCC, clinical genetics, bioinformatics
- **Tertiary**: precision medicine, genetic variants, evidence-based medicine

### 2. Open Graph Tags (Social Media Sharing)

```html
<meta property="og:type" content="website">
<meta property="og:title" content="...">
<meta property="og:description" content="...">
<meta property="og:url" content="...">
<meta property="og:image" content="...">
```

**Purpose**: Control how links appear when shared on Facebook, LinkedIn, Slack, etc.

**Key Features**:
- Separate OG title (more casual/provocative) vs page title (SEO-focused)
- Comprehensive description highlighting key features
- Logo image (192x192) - **Note**: Recommended upgrade to 1200x630 for optimal display

### 3. Twitter Card Tags

```html
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="...">
<meta name="twitter:description" content="...">
<meta name="twitter:image" content="...">
```

**Purpose**: Enhanced Twitter link previews.

**Card Type**: `summary` (square image) - using 192x192 logo.

**Note**: Twitter automatically falls back to Open Graph tags if Twitter-specific tags are missing, but we include both for explicit control.

### 4. JSON-LD Structured Data

#### WebApplication Schema

```json
{
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "Gene Curator",
  "applicationCategory": "HealthcareApplication",
  "softwareVersion": "2.0.0",
  ...
}
```

**Purpose**: Provide semantic information about the application to search engines.

**Key Fields**:
- `applicationCategory`: "HealthcareApplication" (most specific applicable type)
- `offers`: Price $0 (free/open-source)
- `featureList`: Core capabilities in human-readable format
- `audience`: Clinical genetics teams, researchers, bioinformaticians
- `programmingLanguage`: Python, JavaScript (for developers)
- `license`: MIT (open-source)

#### SoftwareSourceCode Schema

```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareSourceCode",
  "codeRepository": "https://github.com/halbritter-lab/gene-curator",
  "programmingLanguage": ["Python", "JavaScript", "Vue.js"],
  ...
}
```

**Purpose**: Additional context for developers and code search engines.

### 5. Mobile & PWA Meta Tags

```html
<meta name="theme-color" content="#1976D2">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Gene Curator">
```

**Purpose**: Optimize mobile web app experience and iOS home screen installation.

### 6. Performance Optimization

```html
<link rel="preconnect" href="https://fonts.googleapis.com" crossorigin>
<link rel="dns-prefetch" href="https://fonts.googleapis.com">
<link rel="preload" href="/img/logo.png" as="image" fetchpriority="high">
```

**Purpose**: Reduce initial page load time by preloading critical resources.

**Techniques**:
- `preconnect`: Early connection to external domains (fonts)
- `dns-prefetch`: DNS resolution for external resources
- `preload`: Priority loading for critical assets

### 7. Robots.txt

```
User-agent: *
Allow: /
Disallow: /api/
```

**Purpose**: Guide search engine crawlers on what to index.

**Strategy**:
- Allow indexing of all user-facing pages
- Disallow API endpoints to save crawl budget
- Disallow test/debug URLs

## Testing & Validation

### 1. Open Graph Testing

**Facebook Sharing Debugger**:
```
https://developers.facebook.com/tools/debug/
```

**LinkedIn Post Inspector**:
```
https://www.linkedin.com/post-inspector/
```

### 2. Twitter Card Validator

```
https://cards-dev.twitter.com/validator
```

### 3. Structured Data Testing

**Google Rich Results Test**:
```
https://search.google.com/test/rich-results
```

**Schema.org Validator**:
```
https://validator.schema.org/
```

### 4. General SEO Audit

**PageSpeed Insights**:
```
https://pagespeed.web.dev/
```

**Lighthouse** (Chrome DevTools):
```
Run: Lighthouse → Performance + SEO + Best Practices
```

## Future Enhancements

### 1. Upgrade Open Graph Image (Priority: Medium)

**Current**: 192x192 logo
**Recommended**: 1200x630 banner image

**Benefits**:
- Larger, more prominent social media previews
- Better branding opportunity
- Supports Twitter `summary_large_image` card type

**Implementation**:
1. Design 1200x630 banner with:
   - Gene Curator logo
   - Tagline: "Methodology-Agnostic Genetic Curation"
   - Key features icons/text
   - Halbritter Lab branding
2. Export as PNG or JPEG (< 5MB)
3. Place in `/frontend/public/img/og-image.png`
4. Update meta tags:
   ```html
   <meta property="og:image" content="https://your-domain.com/img/og-image.png">
   <meta property="og:image:width" content="1200">
   <meta property="og:image:height" content="630">
   <meta name="twitter:card" content="summary_large_image">
   ```

### 2. Dynamic Meta Tags (Priority: High)

**Current**: Static meta tags in index.html
**Recommended**: Dynamic per-route meta tags

**Use Case**: Different pages should have unique titles/descriptions.

**Implementation**:
- Install `@vueuse/head` or use Vue Router meta fields
- Create meta composable:
  ```javascript
  // composables/useSeoMeta.js
  import { useHead } from '@vueuse/head'

  export function useSeoMeta({ title, description, image, url }) {
    useHead({
      title: title || 'Gene Curator',
      meta: [
        { name: 'description', content: description },
        { property: 'og:title', content: title },
        { property: 'og:description', content: description },
        { property: 'og:image', content: image },
        { property: 'og:url', content: url }
      ]
    })
  }
  ```
- Use in components:
  ```javascript
  useSeoMeta({
    title: 'Curation Dashboard - Gene Curator',
    description: 'View and manage gene-disease curations...'
  })
  ```

### 3. XML Sitemap (Priority: Medium)

**Purpose**: Help search engines discover all pages efficiently.

**Implementation**:
1. Create `/frontend/public/sitemap.xml`:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
     <url>
       <loc>https://your-domain.com/</loc>
       <lastmod>2025-10-13</lastmod>
       <changefreq>weekly</changefreq>
       <priority>1.0</priority>
     </url>
     <url>
       <loc>https://your-domain.com/dashboard</loc>
       <changefreq>daily</changefreq>
       <priority>0.8</priority>
     </url>
   </urlset>
   ```
2. Update robots.txt:
   ```
   Sitemap: https://your-domain.com/sitemap.xml
   ```

### 4. Schema.org Dataset Markup (Priority: Low)

**Use Case**: If Gene Curator hosts downloadable datasets of gene-disease relationships.

**Implementation**:
```json
{
  "@context": "https://schema.org",
  "@type": "Dataset",
  "name": "ClinGen Gene-Disease Validity Classifications",
  "description": "Curated gene-disease associations with evidence ratings",
  "url": "https://your-domain.com/datasets/gene-disease",
  "keywords": ["gene-disease", "ClinGen", "genetic classification"],
  "license": "https://creativecommons.org/licenses/by/4.0/",
  "distribution": {
    "@type": "DataDownload",
    "encodingFormat": "application/json",
    "contentUrl": "https://your-domain.com/api/export/gene-disease.json"
  }
}
```

## SEO Monitoring & Maintenance

### Regular Tasks

1. **Monthly**:
   - Check Google Search Console for crawl errors
   - Review search performance (impressions, clicks, CTR)
   - Monitor structured data errors

2. **Quarterly**:
   - Re-validate Open Graph tags with sharing debuggers
   - Update software version in structured data
   - Review and update keywords based on search trends

3. **Annually**:
   - Comprehensive SEO audit
   - Update canonical URLs if domain changes
   - Refresh structured data with new features

### Key Metrics to Track

- **Organic Search Traffic**: Google Analytics
- **Search Console Impressions**: Trend over time
- **Click-Through Rate (CTR)**: Target > 2%
- **Average Position**: Target < 10 (first page)
- **Structured Data Coverage**: Target 100% valid
- **Page Load Time**: Target < 3 seconds

## References

### Best Practices Followed

1. **Google Search Central**: [Structured Data Guidelines](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data)
2. **Schema.org**: [WebApplication](https://schema.org/WebApplication), [SoftwareSourceCode](https://schema.org/SoftwareSourceCode)
3. **Open Graph Protocol**: [og:image specifications](https://ogp.me/)
4. **Twitter Cards**: [Summary Card documentation](https://developer.x.com/en/docs/twitter-for-websites/cards/overview/summary)
5. **Vue 3 SEO**: [CloudDevs Guide](https://clouddevs.com/vue/seo-meta-tags/)

### Inspiration

- **Phentrieve**: JSON-LD structured data with HealthcareApplication category
- **Nuxt SEO**: Open Graph best practices

## Troubleshooting

### Issue: Open Graph image not loading in social media previews

**Solution**:
1. Ensure image URL is absolute (includes https://domain.com)
2. Image must be publicly accessible (no authentication required)
3. Image size < 5MB
4. Clear social media cache:
   - Facebook: Use Sharing Debugger
   - LinkedIn: Post Inspector
   - Twitter: Card Validator

### Issue: Structured data errors in Google Search Console

**Solution**:
1. Validate JSON-LD with [validator.schema.org](https://validator.schema.org/)
2. Check for missing required properties
3. Ensure proper escaping of quotes in JSON
4. Use Google's Rich Results Test

### Issue: Low search rankings despite good metadata

**Possible Causes**:
1. **Content Quality**: Ensure pages have substantial, unique content
2. **Backlinks**: Build quality backlinks from reputable sources
3. **Performance**: Improve page load speed (< 3s)
4. **Mobile Optimization**: Ensure responsive design
5. **Fresh Content**: Regular updates signal active maintenance

---

**Implementation Status**: ✅ **Complete**
**Issue**: #42
**Commit**: [reference commit hash]
**Next Review**: After deployment to production domain
