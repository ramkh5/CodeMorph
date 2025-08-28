# Demo Case

This script defines a function `run()` that asynchronously generates `ResultDto` objects.  
- Each `ResultDto` has a `message` (string) and `value` (integer).  
- The generator yields 3 results with incrementing values.  
- Intended usage is iteration via `async for`.

Example:
```python
async for item in run():
    print(item.message, item.value)
