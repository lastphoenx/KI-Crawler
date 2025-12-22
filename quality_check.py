"""Deep quality check: Compare log URLs with DOCX content"""
from docx import Document
import re

print("=" * 80)
print("QUALITY CHECK: Log URLs vs DOCX Content")
print("=" * 80)

# Parse log for all fetched URLs
with open('output/allpcloud.log', 'r', encoding='utf-8') as f:
    log_lines = f.readlines()

fetched_urls = set()
for line in log_lines:
    if '✓ Fetched:' in line:
        match = re.search(r'✓ Fetched: (https?://[^\s]+)', line)
        if match:
            fetched_urls.add(match.group(1))

print(f"\n📊 Found {len(fetched_urls)} unique fetched URLs in log")

# Parse DOCX for all URLs and their content
doc = Document('output/allpcloud.docx')
docx_content = {}
current_url = None
current_content = []

for para in doc.paragraphs:
    text = para.text.strip()
    
    # Check if this is a URL line
    if text.startswith('URL:'):
        # Save previous entry
        if current_url:
            docx_content[current_url] = '\n'.join(current_content)
        
        # Start new entry
        current_url = text.replace('URL:', '').strip()
        current_content = []
    elif current_url and text and not text.startswith('Web Crawl') and not text.startswith('Crawl Information'):
        # Collect content for current URL
        current_content.append(text)

# Save last entry
if current_url:
    docx_content[current_url] = '\n'.join(current_content)

print(f"📄 Found {len(docx_content)} URLs with content in DOCX")

# Compare
print("\n" + "=" * 80)
print("CONTENT ANALYSIS")
print("=" * 80)

missing_in_docx = []
empty_content = []
has_code_examples = []
no_code_examples = []
good_content = []

for url in sorted(fetched_urls):
    if url not in docx_content:
        missing_in_docx.append(url)
    else:
        content = docx_content[url]
        content_length = len(content)
        
        # Check for empty or minimal content
        if content_length < 50 or 'No content extracted' in content:
            empty_content.append((url, content_length))
        else:
            # Check for code examples
            has_code = any(keyword in content.lower() for keyword in ['```', 'example', 'code', 'method', 'parameter', 'response', 'request'])
            
            if has_code:
                has_code_examples.append((url, content_length))
                if content_length > 500:
                    good_content.append((url, content_length))
            else:
                no_code_examples.append((url, content_length))

print(f"\n✅ Good content (>500 chars with API info): {len(good_content)}")
print(f"📝 Has code/API keywords: {len(has_code_examples)}")
print(f"📭 No code examples: {len(no_code_examples)}")
print(f"⚠️ Empty/minimal content: {len(empty_content)}")
print(f"❌ Missing in DOCX: {len(missing_in_docx)}")

# Show examples
if good_content:
    print(f"\n✅ Examples of GOOD content:")
    for url, length in good_content[:5]:
        print(f"   {url} ({length} chars)")
        # Show first 200 chars
        content_preview = docx_content[url][:200].replace('\n', ' ')
        print(f"   → {content_preview}...")

if empty_content:
    print(f"\n⚠️ Examples of EMPTY/MINIMAL content:")
    for url, length in empty_content[:5]:
        print(f"   {url} ({length} chars)")
        if url in docx_content:
            print(f"   → {docx_content[url][:100]}")

if no_code_examples:
    print(f"\n📭 Examples WITHOUT code (might be category pages):")
    for url, length in no_code_examples[:5]:
        print(f"   {url} ({length} chars)")

if missing_in_docx:
    print(f"\n❌ Missing in DOCX:")
    for url in missing_in_docx[:10]:
        print(f"   {url}")

# Calculate quality score
total_urls = len(fetched_urls)
quality_score = (len(good_content) / total_urls * 100) if total_urls > 0 else 0

print("\n" + "=" * 80)
print("QUALITY SCORE")
print("=" * 80)
print(f"\n{'█' * int(quality_score/2)}{'░' * (50-int(quality_score/2))} {quality_score:.1f}%")
print(f"\n{len(good_content)} out of {total_urls} URLs have rich content with API descriptions")

if quality_score > 80:
    print("\n🎉 EXCELLENT! Most pages have detailed API documentation.")
elif quality_score > 60:
    print("\n👍 GOOD! Majority of pages have useful content.")
elif quality_score > 40:
    print("\n⚠️ FAIR! Some pages are missing content.")
else:
    print("\n❌ POOR! Many pages have no or minimal content.")

# Method-specific check
print("\n" + "=" * 80)
print("METHOD PAGES CHECK (most important)")
print("=" * 80)

method_urls = [url for url in fetched_urls if '/methods/' in url and not url.endswith('/methods/')]
method_with_content = [url for url in method_urls if url in docx_content and len(docx_content[url]) > 200]

print(f"\nMethod pages found: {len(method_urls)}")
print(f"Method pages with content: {len(method_with_content)}")

if method_urls:
    print(f"\nSample method page:")
    sample_url = method_urls[0] if method_urls else None
    if sample_url and sample_url in docx_content:
        print(f"URL: {sample_url}")
        print(f"Content length: {len(docx_content[sample_url])} chars")
        print(f"Preview:\n{docx_content[sample_url][:500]}")
