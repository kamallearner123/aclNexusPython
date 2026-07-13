import re

with open('templates/tasks/kanban.html', 'r') as f:
    content = f.read()

# We will replace the entire <div class="flex gap-6 overflow-x-auto pb-6 items-start"... block until <!-- SortableJS -->
new_html = """<div class="flex gap-4 overflow-x-auto pb-6 items-start" style="min-height: 70vh;">
    <!-- Backlog Column -->
    <div class="w-[300px] flex-shrink-0 flex flex-col bg-[#f4f5f7] border border-gray-200">
        <div class="px-4 py-3 bg-[#6984c1] text-white text-center font-bold text-lg">
            Backlog
        </div>
        <div class="p-3 task-column" id="backlog-col" data-status="BACKLOG">
            {% for task in backlog %}
            <div class="bg-white border border-gray-200 border-l-[6px] border-l-[#6984c1] mb-3 cursor-grab task-card shadow-sm rounded-sm" data-task-id="{{ task.pk }}">
                <div class="p-3">
                    <h6 class="text-sm font-semibold text-gray-800 mb-3"><a href="{% url 'task_detail' task.pk %}" class="hover:text-brand-600 transition-colors">{{ task.title }}</a></h6>
                    <div class="flex items-center text-xs text-gray-500 mb-3">
                        {% if task.assignee %}
                            <div class="w-5 h-5 rounded-full bg-purple-700 text-white flex items-center justify-center font-bold text-[10px] mr-2" title="{{ task.assignee.email }}">{{ task.assignee.email|make_list|first|upper }}</div>
                        {% else %}
                            <div class="w-5 h-5 rounded-full bg-gray-400 text-white flex items-center justify-center font-bold text-[10px] mr-2">U</div>
                        {% endif %}
                        <span class="mr-2 border rounded-full px-1.5 py-0.5 bg-gray-50 text-[9px]">{{ task.story_points|default:"0" }} pt</span>
                        <span>Pending</span>
                    </div>
                    <div class="w-full bg-gray-100 h-1.5 rounded-full mb-3">
                        <div class="bg-[#6984c1] h-1.5 rounded-full" style="width: 10%"></div>
                    </div>
                    <div class="flex justify-end gap-2 text-gray-400">
                        <i data-lucide="message-square" class="w-3.5 h-3.5"></i>
                        <i data-lucide="paperclip" class="w-3.5 h-3.5"></i>
                    </div>
                </div>
            </div>
            {% empty %}
            {% endfor %}
            
            {% if can_create_task %}
            <a href="{% url 'task_create' %}?project_id={{ project.pk }}" class="block text-center text-gray-400 hover:text-gray-600 font-medium text-sm py-2 transition-colors">
                + Add Task
            </a>
            {% endif %}
        </div>
    </div>

    <!-- In Progress Column -->
    <div class="w-[300px] flex-shrink-0 flex flex-col bg-[#f4f5f7] border border-gray-200">
        <div class="px-4 py-3 bg-[#4bb1f4] text-white text-center font-bold text-lg">
            In Progress
        </div>
        <div class="p-3 task-column" id="inprogress-col" data-status="IN_PROGRESS">
            {% for task in in_progress %}
            <div class="bg-white border border-gray-200 border-l-[6px] border-l-[#4bb1f4] mb-3 cursor-grab task-card shadow-sm rounded-sm" data-task-id="{{ task.pk }}">
                <div class="p-3">
                    <h6 class="text-sm font-semibold text-gray-800 mb-3"><a href="{% url 'task_detail' task.pk %}" class="hover:text-brand-600 transition-colors">{{ task.title }}</a></h6>
                    <div class="flex items-center text-xs text-gray-500 mb-3">
                        {% if task.assignee %}
                            <div class="w-5 h-5 rounded-full bg-purple-700 text-white flex items-center justify-center font-bold text-[10px] mr-2" title="{{ task.assignee.email }}">{{ task.assignee.email|make_list|first|upper }}</div>
                        {% else %}
                            <div class="w-5 h-5 rounded-full bg-gray-400 text-white flex items-center justify-center font-bold text-[10px] mr-2">U</div>
                        {% endif %}
                        <span class="mr-2 border rounded-full px-1.5 py-0.5 bg-gray-50 text-[9px]">{{ task.story_points|default:"0" }} pt</span>
                        <span>Ongoing</span>
                    </div>
                    <div class="w-full bg-gray-100 h-1.5 rounded-full mb-3">
                        <div class="bg-[#8ac63a] h-1.5 rounded-full" style="width: 50%"></div>
                    </div>
                    <div class="flex justify-end gap-2 text-gray-400">
                        <i data-lucide="message-square" class="w-3.5 h-3.5"></i>
                        <i data-lucide="paperclip" class="w-3.5 h-3.5"></i>
                    </div>
                </div>
            </div>
            {% empty %}
            {% endfor %}
            
            {% if can_create_task %}
            <a href="{% url 'task_create' %}?project_id={{ project.pk }}" class="block text-center text-gray-400 hover:text-gray-600 font-medium text-sm py-2 transition-colors">
                + Add Task
            </a>
            {% endif %}
        </div>
    </div>

    <!-- In Review Column -->
    <div class="w-[300px] flex-shrink-0 flex flex-col bg-[#f4f5f7] border border-gray-200">
        <div class="px-4 py-3 bg-[#f2a741] text-white text-center font-bold text-lg">
            In Review
        </div>
        <div class="p-3 task-column" id="inreview-col" data-status="REVIEW">
            {% for task in in_review %}
            <div class="bg-white border border-gray-200 border-l-[6px] border-l-[#f2a741] mb-3 cursor-grab task-card shadow-sm rounded-sm" data-task-id="{{ task.pk }}">
                <div class="p-3">
                    <h6 class="text-sm font-semibold text-gray-800 mb-3"><a href="{% url 'task_detail' task.pk %}" class="hover:text-brand-600 transition-colors">{{ task.title }}</a></h6>
                    <div class="flex items-center text-xs text-gray-500 mb-3">
                        {% if task.assignee %}
                            <div class="w-5 h-5 rounded-full bg-purple-700 text-white flex items-center justify-center font-bold text-[10px] mr-2" title="{{ task.assignee.email }}">{{ task.assignee.email|make_list|first|upper }}</div>
                        {% else %}
                            <div class="w-5 h-5 rounded-full bg-gray-400 text-white flex items-center justify-center font-bold text-[10px] mr-2">U</div>
                        {% endif %}
                        <span class="mr-2 border rounded-full px-1.5 py-0.5 bg-gray-50 text-[9px]">{{ task.story_points|default:"0" }} pt</span>
                        <span>Reviewing</span>
                    </div>
                    <div class="w-full bg-gray-100 h-1.5 rounded-full mb-3">
                        <div class="bg-[#8ac63a] h-1.5 rounded-full" style="width: 80%"></div>
                    </div>
                    <div class="flex justify-end gap-2 text-gray-400">
                        <i data-lucide="message-square" class="w-3.5 h-3.5"></i>
                        <i data-lucide="paperclip" class="w-3.5 h-3.5"></i>
                    </div>
                </div>
            </div>
            {% empty %}
            {% endfor %}
            
            {% if can_create_task %}
            <a href="{% url 'task_create' %}?project_id={{ project.pk }}" class="block text-center text-gray-400 hover:text-gray-600 font-medium text-sm py-2 transition-colors">
                + Add Task
            </a>
            {% endif %}
        </div>
    </div>

    <!-- Completed Column -->
    <div class="w-[300px] flex-shrink-0 flex flex-col bg-[#f4f5f7] border border-gray-200">
        <div class="px-4 py-3 bg-[#a2df6a] text-white text-center font-bold text-lg">
            Completed
        </div>
        <div class="p-3 task-column" id="completed-col" data-status="COMPLETED">
            {% for task in completed %}
            <div class="bg-white border border-gray-200 border-l-[6px] border-l-[#a2df6a] mb-3 cursor-grab task-card shadow-sm rounded-sm" data-task-id="{{ task.pk }}">
                <div class="p-3">
                    <h6 class="text-sm font-semibold text-gray-800 mb-3"><a href="{% url 'task_detail' task.pk %}" class="hover:text-brand-600 transition-colors">{{ task.title }}</a></h6>
                    <div class="flex items-center text-xs text-gray-500 mb-3">
                        {% if task.assignee %}
                            <div class="w-5 h-5 rounded-full bg-purple-700 text-white flex items-center justify-center font-bold text-[10px] mr-2" title="{{ task.assignee.email }}">{{ task.assignee.email|make_list|first|upper }}</div>
                        {% else %}
                            <div class="w-5 h-5 rounded-full bg-gray-400 text-white flex items-center justify-center font-bold text-[10px] mr-2">U</div>
                        {% endif %}
                        <span class="mr-2 border rounded-full px-1.5 py-0.5 bg-gray-50 text-[9px]">{{ task.story_points|default:"0" }} pt</span>
                        <span>Finished</span>
                    </div>
                    <div class="w-full bg-gray-100 h-1.5 rounded-full mb-3">
                        <div class="bg-[#a2df6a] h-1.5 rounded-full" style="width: 100%"></div>
                    </div>
                    <div class="flex justify-end gap-2 text-gray-400">
                        <i data-lucide="message-square" class="w-3.5 h-3.5"></i>
                        <i data-lucide="paperclip" class="w-3.5 h-3.5"></i>
                    </div>
                </div>
            </div>
            {% empty %}
            {% endfor %}
            
            {% if can_create_task %}
            <a href="{% url 'task_create' %}?project_id={{ project.pk }}" class="block text-center text-gray-400 hover:text-gray-600 font-medium text-sm py-2 transition-colors">
                + Add Task
            </a>
            {% endif %}
        </div>
    </div>
</div>
"""

pattern = re.compile(r'<div class="flex gap-6 overflow-x-auto pb-6 items-start" style="min-height: 70vh;">.*?</div>\s*<!-- SortableJS -->', re.DOTALL)
content = pattern.sub(new_html + "\n<!-- SortableJS -->", content)

with open('templates/tasks/kanban.html', 'w') as f:
    f.write(content)

print("Updated")
