# Memory Profiling Documentation

## Overview

The Memory Profiler module tracks memory usage during crawling operations, helping identify memory leaks and optimize resource consumption. It provides snapshots, checkpoints, and detailed reports.

## Installation

Ensure `psutil` is installed:

```bash
pip install psutil
```

## Usage

### Basic Usage

```python
from memory_profiler import MemoryProfiler

profiler = MemoryProfiler()
profiler.start()

# Your code here
crawled_pages = crawler.crawl()

profiler.checkpoint('after_crawl')

# More code
pages_saved = save_to_docx(crawled_pages)

profiler.checkpoint('after_docx')

# Print report
print(profiler.report())
```

### Using the Decorator

```python
from memory_profiler import profile_memory

@profile_memory
def crawl_and_process():
    crawler = Crawler()
    pages, errors = crawler.crawl()
    return pages

pages = crawl_and_process()
```

## API Reference

### MemoryProfiler Class

#### `__init__()`
Initializes the memory profiler for the current process.

#### `start() -> Dict`
Records the initial memory snapshot.

**Returns:**
- Dictionary with keys: `timestamp`, `rss_mb`, `vms_mb`

**Example:**
```python
profiler = MemoryProfiler()
start = profiler.start()
print(f"Start memory: {start['rss_mb']:.2f} MB")
```

#### `checkpoint(name: str) -> Dict`
Records a memory snapshot at a named checkpoint.

**Parameters:**
- `name`: Unique identifier for this checkpoint

**Returns:**
- Dictionary with keys: `timestamp`, `rss_mb`, `vms_mb`, `delta_mb` (if start recorded)

**Example:**
```python
profiler.checkpoint('before_parallel_crawl')
# ... heavy operation ...
profiler.checkpoint('after_parallel_crawl')
```

#### `get_peak_memory() -> float`
Returns the peak memory usage across all snapshots in MB.

```python
peak = profiler.get_peak_memory()
print(f"Peak memory usage: {peak:.2f} MB")
```

#### `get_memory_increase() -> float`
Returns the total memory increase from start to current in MB.

```python
increase = profiler.get_memory_increase()
print(f"Memory increase: {increase:+.2f} MB")
```

#### `report() -> str`
Generates a formatted memory profiling report.

```python
report = profiler.report()
print(report)
```

Output example:
```
============================================================
MEMORY PROFILING REPORT
============================================================

[start] @ 2025-12-19T10:30:45.123456
  RSS: 45.23 MB
  VMS: 120.45 MB

[after_crawl] @ 2025-12-19T10:30:48.456789
  RSS: 156.78 MB
  VMS: 234.56 MB
  Δ from start: +111.55 MB

[after_docx] @ 2025-12-19T10:30:52.789123
  RSS: 143.92 MB
  VMS: 219.34 MB
  Δ from start: +98.69 MB

============================================================
Peak Memory: 156.78 MB
Total Increase: +98.69 MB
============================================================
```

#### `log_report()`
Logs the memory profiling report using the logging module.

```python
profiler.log_report()
```

## Memory Metrics Explained

- **RSS (Resident Set Size)**: Physical memory currently used by the process in MB
- **VMS (Virtual Memory Size)**: Total virtual memory allocated to the process in MB
- **Δ (Delta)**: Change in memory from the start checkpoint in MB

## Integration with Crawler

To profile the entire crawl pipeline:

```python
from crawler import Crawler
from memory_profiler import MemoryProfiler

profiler = MemoryProfiler()
profiler.start()

crawler = Crawler()
pages, errors = crawler.crawl()
profiler.checkpoint('crawl_complete')

# Parallel fetching uses ThreadPoolExecutor, monitor memory spike
print(f"Pages fetched: {len(pages)}")
print(f"Memory at completion: {profiler.get_memory_increase():+.2f} MB")

profiler.log_report()
```

## Expected Memory Usage

For the pCloud API Crawler:

| Operation | Typical Memory | Peak Memory |
|-----------|---|---|
| Startup | ~40 MB | ~40 MB |
| Navigation phase | +10-20 MB | ~50-60 MB |
| Parallel crawling (5 workers) | +80-120 MB | ~150-180 MB |
| DOCX generation | +20-40 MB | ~180-220 MB |
| **Total (Full pipeline)** | **~40-60 MB (base)** | **~200-250 MB** |

## Best Practices

1. **Always call `start()`** before operations to establish a baseline
2. **Use checkpoints strategically** at phase boundaries (crawl, parse, generate)
3. **Monitor parallel operations** - ThreadPoolExecutor can cause memory spikes
4. **Check for memory leaks** - memory should stabilize, not continuously grow
5. **Log reports at pipeline exit** for post-mortem analysis

## Optimization Tips

### If memory usage is too high:

1. **Reduce parallel workers**
   ```python
   crawler = Crawler(max_workers=3)  # Default is 5
   ```

2. **Process in batches**
   ```python
   batch_size = 10
   for i in range(0, len(method_urls), batch_size):
       batch = method_urls[i:i+batch_size]
       # Process batch
   ```

3. **Clear cache between operations**
   ```python
   import gc
   profiler.checkpoint('before_gc')
   gc.collect()
   profiler.checkpoint('after_gc')
   ```

4. **Use generators instead of lists**
   ```python
   def get_pages():
       for page in pages:
           yield process_page(page)
   ```

## Performance Baseline

Crawling 117 pCloud API methods:

- **Sequential (1 worker)**: ~1170 seconds, ~150 MB peak
- **Parallel (5 workers)**: ~234 seconds, ~220 MB peak
- **Memory overhead for parallelization**: +70 MB

## Debugging Memory Issues

### Find memory spikes:

```python
profiler = MemoryProfiler()
profiler.start()

profiler.checkpoint('phase_1')
# ... do work ...

profiler.checkpoint('phase_2')
# ... more work ...

profiler.checkpoint('phase_3')

# Analyze results
for name, data in profiler.snapshots.items():
    if data.get('delta_mb', 0) > 50:
        print(f"⚠️ Large spike at {name}: {data['delta_mb']:+.2f} MB")
```

### Monitor specific operations:

```python
from memory_profiler import profile_memory

@profile_memory
def load_all_html_to_memory():
    """This will report memory before/after"""
    all_html = [fetch_url(url) for url in urls]
    return all_html
```

## Future Enhancements

- [ ] CPU profiling integration
- [ ] Memory profiling by operation type
- [ ] Automatic memory leak detection
- [ ] Integration with APScheduler for periodic monitoring
- [ ] Export to CSV/JSON for analysis
