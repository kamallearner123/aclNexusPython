import os

replacements = {
    'bg-white shadow-soft ring-1 ring-gray-900/5 rounded-xl-body': 'p-6',
    'bg-white shadow-soft ring-1 ring-gray-900/5 rounded-xl-header': 'border-b border-gray-100 px-6 py-4',
    'bg-white shadow-soft ring-1 ring-gray-900/5 rounded-xl-footer': 'border-t border-gray-100 px-6 py-4 bg-gray-50 rounded-b-xl',
    'bg-white shadow-soft ring-1 ring-gray-900/5 rounded-xl-title': 'text-lg font-semibold text-gray-900',
    'bg-white shadow-soft ring-1 ring-gray-900/5 rounded-xl-text': 'text-sm text-gray-500 mt-2',
}

for root, _, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r') as f:
                content = f.read()
                
            original_content = content
            for old, new in replacements.items():
                content = content.replace(old, new)
                
            if content != original_content:
                with open(path, 'w') as f:
                    f.write(content)
                print(f"Fixed {path}")
