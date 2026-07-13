import os

filepath = 'templates/projects/detail.html'
with open(filepath, 'r') as f:
    content = f.read()

# Replace border-none and faint rings with solid borders on cards
old_class = "bg-white shadow-soft ring-1 ring-gray-900/5 rounded-xl shadow-soft border-none"
new_class = "bg-white rounded-xl shadow-sm border border-gray-200"

content = content.replace(old_class, new_class)
content = content.replace("border-none", "")

with open(filepath, 'w') as f:
    f.write(content)

filepath_attachments = 'templates/core/includes/attachments.html'
with open(filepath_attachments, 'r') as f:
    content_att = f.read()

content_att = content_att.replace(old_class, new_class)

with open(filepath_attachments, 'w') as f:
    f.write(content_att)
