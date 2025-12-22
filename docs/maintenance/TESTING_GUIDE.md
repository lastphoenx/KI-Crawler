# Testing Guide - Real Crawler Integration

## Quick Start Testing

### 1. Ensure UI is Running
The UI should already be running with hot reload. If not:
```powershell
python main_ui.py
```

Open browser: http://localhost:8080

### 2. Test Simple Crawl

#### Step-by-Step Test
1. **Navigate to "New Crawl"** (click button on dashboard)

2. **Enter a small test URL**:
   - **Recommended**: `https://example.com` (1 page, fast)
   - Or: `https://httpbin.org` (API docs, ~10-20 pages)
   - Avoid large sites for first test

3. **Configure Settings**:
   - Max Pages: `10` (keep it small)
   - Crawl Depth: `2`
   - Other settings: Leave as default

4. **Click "Start Crawl"**
   - Should redirect to Progress Monitor
   - Real-time logs should appear
   - Progress bar should move

5. **Watch Progress**:
   - Current URL should update
   - Page count should increment
   - Speed (pages/second) should show
   - ETA should count down

6. **View Results**:
   - Should auto-redirect when complete
   - Shows real page count
   - Shows actual duration
   - Check for output files

### 3. What to Expect

#### Progress Monitor
```
Status: Crawling: https://example.com/page-1
Pages: 3/10
Errors: 0
Speed: 2.5 p/s
ETA: 0m 3s

Logs:
[12:34:56] 🚀 Starting crawler...
[12:34:57] ✅ Crawled: https://example.com (0.5s)
[12:34:58] ✅ Crawled: https://example.com/about (0.4s)
[12:34:58] ✅ Crawled: https://example.com/contact (0.3s)
...
```

#### Results Page
```
✅ Crawl Complete!

🎉 Crawled 10 pages in 4.2 seconds
• ✅ 10 pages processed
• ❌ 0 errors

Downloads:
📄 DOCX (0.08 MB) [Download button]
📕 PDF (0.15 MB) [Download button]
📊 JSON (State Data) [Download button]

Statistics:
Pages Crawled: 10
Total Errors: 0
Avg Speed: 2.4 p/s
Total Duration: 4.2s
Start Time: 12:34:56
End Time: 12:35:00
```

### 4. Common Test Scenarios

#### Test A: Quick Single Page
```
URL: https://example.com
Max Pages: 1
Expected: Completes in <1 second
```

#### Test B: Small Documentation Site
```
URL: https://httpbin.org
Max Pages: 20
Crawl Depth: 2
Expected: 5-10 seconds, real docs structure
```

#### Test C: Real Documentation (Longer)
```
URL: https://docs.pcloud.com
Max Pages: 100
Crawl Depth: 3
Expected: 30-60 seconds, professional output
```

#### Test D: Template-Based
```
1. Select "pCloud Docs" template
2. URL auto-filled
3. Settings auto-configured
4. Start crawl
Expected: Optimized crawl for pCloud docs
```

### 5. Verification Checklist

#### ✅ Integration Working If:
- [ ] Progress bar moves smoothly
- [ ] Logs appear in real-time
- [ ] Page counter increments
- [ ] Current URL changes
- [ ] Speed is calculated (not 0.0)
- [ ] ETA counts down
- [ ] Auto-redirects to results on completion
- [ ] Results show real numbers
- [ ] Output files exist in `output/` folder

#### ❌ Issues If:
- [ ] Progress stuck at 0%
- [ ] No logs appearing
- [ ] "Crawl not found" error
- [ ] Immediate redirect to results
- [ ] All zeros in statistics
- [ ] No output files created

### 6. Debug Mode

If you need to debug:

#### Check State Manager
```python
# In Python REPL or add to a test script
from services.crawl_state_manager import CrawlStateManager

state_mgr = CrawlStateManager()
states = state_mgr.get_all_states()

for crawl_id, state in states.items():
    print(f"Crawl: {crawl_id}")
    print(f"  Status: {state.status}")
    print(f"  Pages: {state.current_page}/{state.total_pages}")
    print(f"  Errors: {state.errors}")
```

#### Check Output Files
```powershell
# List output directory
Get-ChildItem -Path .\output\ -Recurse | Sort-Object LastWriteTime -Descending | Select-Object -First 10
```

#### View Logs
The UI logs show in the terminal running `main_ui.py`:
```
2025-12-19 12:34:56 - crawler - INFO - Starting crawl for https://example.com
2025-12-19 12:34:57 - crawler - INFO - Discovered 5 pages
2025-12-19 12:34:58 - crawler - INFO - Processing page 1/5
...
```

### 7. Performance Testing

#### Test Parallel Crawling
```
URL: https://httpbin.org
Max Pages: 50
Parallel Limit: 5  # Default: 3
Rate Limit: 0.2    # Default: 0.5

Expected: Faster completion, ~5 requests simultaneously
```

#### Test Rate Limiting
```
URL: https://httpbin.org
Max Pages: 20
Rate Limit: 2.0    # 2 seconds between requests

Expected: Slower, but respectful of server
```

### 8. Error Testing

#### Test Invalid URL
```
URL: https://this-does-not-exist-12345.com
Expected: Error status, error message in logs
```

#### Test Network Error
```
URL: https://httpstat.us/500
Expected: Handles 500 errors gracefully
```

#### Test Max Pages Limit
```
URL: https://docs.python.org
Max Pages: 5  # Very small
Expected: Stops at 5 pages, doesn't crawl all docs
```

### 9. UI/UX Testing

#### Navigation Flow
1. Dashboard → New Crawl → Progress → Results → Dashboard
2. Test "Back" buttons
3. Test direct URL navigation
4. Test browser back/forward

#### Responsive Design
1. Resize browser window
2. Test on mobile viewport (F12 → Device toolbar)
3. Check cards layout at different widths

#### Real-Time Updates
1. Open multiple browser tabs to same progress page
2. Both should update simultaneously
3. Test WebSocket connection

### 10. Edge Cases

#### Multiple Concurrent Crawls
```
1. Start crawl A (large site, 100 pages)
2. While A is running, start crawl B
3. Both should progress independently
```

#### Stop During Crawl
```
1. Start a large crawl
2. Navigate away during progress
3. Return later - should still show progress
```

#### Browser Refresh
```
1. Start crawl
2. Refresh browser during progress
3. Should reconnect and continue showing progress
```

## Expected Behavior

### ✅ Successful Integration Shows:
- Real URLs being crawled
- Actual page discovery
- True error counts
- Real timing/duration
- Actual output files
- Consistent state across pages

### ❌ Still Mock Data Would Show:
- Static "Crawling: page-1, page-2, page-3"
- Exact same numbers every time
- No actual files created
- Progress always same duration
- No real URL changes

## Troubleshooting

### "ImportError: cannot import name 'DocumentationCrawler'"
**Fixed**: Changed to `Crawler` class name

### "Crawl not found"
**Cause**: State not created or lost
**Fix**: Check `crawler_service.start_crawl()` creates state

### Progress stuck at 0%
**Cause**: State not updating
**Fix**: Check `_run_crawler_thread()` callback

### No logs appearing
**Cause**: Log updates not working
**Fix**: Check `state_manager.add_log()` calls

### Files not showing
**Cause**: Output path incorrect
**Fix**: Check `config['output_name']` and output directory

## Success Criteria

### Option A (Real Crawler) ✅ Complete When:
- [x] CrawlStateManager created
- [x] CrawlerService uses real Crawler
- [x] Progress Monitor polls real state
- [x] Results show actual data
- [x] Files are created in output/

### Option B (Test UI) ✅ Ready When:
- [x] Can start a real crawl
- [x] See real-time progress
- [x] View actual results
- [x] Navigate full flow
- [x] No mock data visible

## Next Test Session

Once basic integration is verified, test:
1. **File Downloads**: Click download buttons
2. **Error Handling**: Crawl invalid URLs
3. **Performance**: Large crawls (500+ pages)
4. **Concurrent**: Multiple crawls at once
5. **Templates**: Each preset template

## Questions to Answer During Testing

1. **Performance**: Is polling every 500ms smooth?
2. **UI/UX**: Does progress feel responsive?
3. **Accuracy**: Are metrics accurate?
4. **Reliability**: Does it handle errors well?
5. **Completeness**: Is any data still mocked?

## Test Report Template

```
Test Date: [DATE]
Tested By: [NAME]

Test URL: [URL]
Configuration: [MAX_PAGES, DEPTH, etc.]
Duration: [SECONDS]
Pages Crawled: [COUNT]
Errors: [COUNT]

✅ Working:
- [ ] List what worked

❌ Issues:
- [ ] List any problems

📝 Notes:
- [Any observations]
```

## Ready to Test!

The integration is complete. Start with a simple test (example.com) and work up to larger sites. The UI should now show real crawler data throughout!
