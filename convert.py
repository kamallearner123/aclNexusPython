import os
import re

replacements = {
    r'class="card([^"]*)"': r'class="bg-white shadow-soft ring-1 ring-gray-900/5 rounded-xl\1"',
    r'class="card-body([^"]*)"': r'class="p-6\1"',
    r'class="card-header([^"]*)"': r'class="border-b border-gray-100 px-6 py-4\1"',
    r'class="card-footer([^"]*)"': r'class="border-t border-gray-100 px-6 py-4 bg-gray-50 rounded-b-xl\1"',
    r'class="card-title([^"]*)"': r'class="text-lg font-semibold text-gray-900\1"',
    r'class="card-text([^"]*)"': r'class="text-sm text-gray-500 mt-2\1"',
    
    r'class="btn btn-primary([^"]*)"': r'class="inline-flex items-center justify-center rounded-md bg-brand-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 transition-colors\1"',
    r'class="btn btn-outline-primary([^"]*)"': r'class="inline-flex items-center justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-brand-600 shadow-sm ring-1 ring-inset ring-brand-300 hover:bg-brand-50 transition-colors\1"',
    r'class="btn btn-sm btn-primary([^"]*)"': r'class="inline-flex items-center justify-center rounded-md bg-brand-600 px-2.5 py-1.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-500 transition-colors\1"',
    r'class="btn btn-sm btn-outline-primary([^"]*)"': r'class="inline-flex items-center justify-center rounded-md bg-white px-2.5 py-1.5 text-sm font-semibold text-brand-600 shadow-sm ring-1 ring-inset ring-brand-300 hover:bg-brand-50 transition-colors\1"',
    r'class="btn btn-secondary([^"]*)"': r'class="inline-flex items-center justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 transition-colors\1"',
    r'class="btn btn-danger([^"]*)"': r'class="inline-flex items-center justify-center rounded-md bg-rose-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-rose-500 transition-colors\1"',
    r'class="btn btn-sm btn-danger([^"]*)"': r'class="inline-flex items-center justify-center rounded-md bg-rose-600 px-2.5 py-1.5 text-sm font-semibold text-white shadow-sm hover:bg-rose-500 transition-colors\1"',
    
    r'class="badge bg-success([^"]*)"': r'class="inline-flex items-center rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20\1"',
    r'class="badge bg-primary([^"]*)"': r'class="inline-flex items-center rounded-md bg-brand-50 px-2 py-1 text-xs font-medium text-brand-700 ring-1 ring-inset ring-brand-600/20\1"',
    r'class="badge bg-warning([^"]*)"': r'class="inline-flex items-center rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-600/20\1"',
    r'class="badge bg-danger([^"]*)"': r'class="inline-flex items-center rounded-md bg-rose-50 px-2 py-1 text-xs font-medium text-rose-700 ring-1 ring-inset ring-rose-600/20\1"',
    r'class="badge bg-secondary([^"]*)"': r'class="inline-flex items-center rounded-md bg-gray-50 px-2 py-1 text-xs font-medium text-gray-600 ring-1 ring-inset ring-gray-500/10\1"',
    r'class="badge bg-info([^"]*)"': r'class="inline-flex items-center rounded-md bg-sky-50 px-2 py-1 text-xs font-medium text-sky-700 ring-1 ring-inset ring-sky-600/20\1"',
    
    r'class="table([^"]*)"': r'class="min-w-full divide-y divide-gray-300\1"',
    r'<thead class="table-light">': r'<thead class="bg-gray-50">',
    
    r'class="d-flex justify-content-between align-items-center([^"]*)"': r'class="flex justify-between items-center\1"',
    r'class="row([^"]*)"': r'class="grid grid-cols-1 md:grid-cols-12 gap-6\1"',
    r'class="col-md-8([^"]*)"': r'class="md:col-span-8\1"',
    r'class="col-md-4([^"]*)"': r'class="md:col-span-4\1"',
    r'class="col-md-6([^"]*)"': r'class="md:col-span-6\1"',
    r'class="col-12([^"]*)"': r'class="col-span-1\1"',
    
    r'class="mb-3([^"]*)"': r'class="mb-4\1"',
    r'class="mb-4([^"]*)"': r'class="mb-6\1"',
    
    r'text-primary': r'text-brand-600',
    r'text-muted': r'text-gray-500',
    r'text-danger': r'text-rose-600',
    r'text-success': r'text-emerald-600',
    r'text-warning': r'text-amber-600',
    
    r'bg-light': r'bg-gray-50',
    r'bg-white': r'bg-white',
    
    r'shadow-sm': r'shadow-soft',
    r'border-0': r'border-none',
    
    r'bi bi-plus-lg': r'lucide-plus',
    r'bi bi-briefcase': r'lucide-briefcase',
    r'bi bi-pencil': r'lucide-pencil',
    r'bi bi-trash': r'lucide-trash-2',
    r'bi bi-folder2-open': r'lucide-folder-open',
}

for root, _, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html') and file != 'base_tailwind.html' and file != 'dashboard.html' and 'registration' not in root:
            path = os.path.join(root, file)
            with open(path, 'r') as f:
                content = f.read()
                
            original_content = content
            for pattern, replacement in replacements.items():
                content = re.sub(pattern, replacement, content)
                
            if content != original_content:
                with open(path, 'w') as f:
                    f.write(content)
                print(f"Updated {path}")
