import os

filepath = 'templates/projects/detail.html'
with open(filepath, 'r') as f:
    content = f.read()

# Replace Repositories & Documents border-none
old_class_repo = "bg-white shadow-soft ring-1 ring-gray-900/5 rounded-xl bg-gray-50 "
new_class_repo = "bg-gray-50 rounded-xl border border-gray-200 "

content = content.replace(old_class_repo, new_class_repo)

with open(filepath, 'w') as f:
    f.write(content)
