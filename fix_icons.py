import os
import re

replacements = [
    (r'class="lucide-([a-zA-Z0-9-]+)([^"]*)"', r'data-lucide="\1" class="w-4 h-4\2"'),
    (r'class="bi bi-([a-zA-Z0-9-]+)([^"]*)"', r'data-lucide="\1" class="w-4 h-4\2"'),
    (r'fs-1', r'text-4xl'),
    (r'fs-2', r'text-3xl'),
    (r'fs-3', r'text-2xl'),
    (r'fs-4', r'text-xl'),
    (r'fs-5', r'text-lg'),
    (r'fs-6', r'text-base'),
    (r'me-1', r'mr-1'),
    (r'me-2', r'mr-2'),
    (r'me-3', r'mr-3'),
    (r'ms-1', r'ml-1'),
    (r'ms-2', r'ml-2'),
    (r'ms-3', r'ml-3'),
    (r'mb-1', r'mb-2'),
    (r'mb-2', r'mb-4'),
    (r'mt-1', r'mt-2'),
    (r'mt-2', r'mt-4'),
    (r'mt-3', r'mt-6'),
    (r'p-3', r'p-4'),
    (r'p-4', r'p-6'),
    (r'py-3', r'py-4'),
    (r'py-4', r'py-6'),
    (r'py-5', r'py-12'),
    (r'px-3', r'px-4'),
    (r'px-4', r'px-6'),
    (r'fw-bold', r'font-bold'),
    (r'fw-semibold', r'font-semibold'),
    (r'text-center', r'text-center'),
    (r'align-items-center', r'items-center'),
    (r'justify-content-between', r'justify-between'),
    (r'justify-content-center', r'justify-center'),
    (r'd-flex', r'flex'),
    (r'd-none', r'hidden'),
    (r'd-lg-none', r'lg:hidden'),
    (r'list-group-item', r'block px-4 py-3 border-b border-gray-100 bg-white hover:bg-gray-50 transition-colors'),
    (r'list-group', r'border border-gray-100 rounded-lg overflow-hidden'),
    (r'rounded-pill', r'rounded-full'),
]

for root, _, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html') and file != 'base_tailwind.html' and file != 'dashboard.html' and 'registration' not in root:
            path = os.path.join(root, file)
            with open(path, 'r') as f:
                content = f.read()
                
            original_content = content
            for pattern, replacement in replacements:
                content = re.sub(pattern, replacement, content)
                
            if content != original_content:
                with open(path, 'w') as f:
                    f.write(content)
                print(f"Updated {path}")
