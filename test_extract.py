#!/usr/bin/env python3
import json

test_response = '''```json
[
  {
    "title": "第一章",
    "page": 1,
    "level": 1
  },
  {
    "title": "第二章",
    "page": 10,
    "level": 1
  }
]
```'''

def extract_json_from_response(response):
    response = response.strip()
    
    # 查找 markdown 代码块
    if '```' in response:
        start_marker = response.find('```')
        if start_marker != -1:
            content_start = response.find('\n', start_marker) + 1
            if content_start == 0:
                content_start = start_marker + 3
                if response[content_start:content_start+4] == 'json':
                    content_start += 4
            
            end_marker = response.find('```', content_start)
            if end_marker != -1:
                json_str = response[content_start:end_marker].strip()
                if json_str.startswith('[') or json_str.startswith('{'):
                    return json_str
    
    # 查找数组
    array_start = response.find('[')
    if array_start != -1:
        array_end = response.rfind(']')
        if array_end > array_start:
            return response[array_start:array_end+1]
    
    return response

result = extract_json_from_response(test_response)
print('提取结果:')
print(result[:100])
print('\n开头字符:', repr(result[:5]))
print('是否以 [ 开头:', result.startswith('['))

parsed = json.loads(result)
print('\n✓ 解析成功! 条目数:', len(parsed))
print('内容:', parsed)
