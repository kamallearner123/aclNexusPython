import re

with open('templates/base.html', 'r') as f:
    content = f.read()

nav_pattern = re.compile(r'<nav class="p-6 space-y-1 mt-4">.*?</nav>', re.DOTALL)

new_nav = """<nav class="p-4 space-y-2 mt-2">
                {% if request.user.is_staff or request.user.is_superuser %}
                <a href="{% url 'dashboard' %}" class="group flex items-center px-4 py-3 mx-2 rounded-xl text-sm font-semibold transition-all duration-300 {% if request.resolver_match.url_name == 'dashboard' %}bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/30 ring-1 ring-white/20 transform scale-[1.02]{% else %}text-gray-500 hover:text-gray-900 hover:bg-white hover:shadow-sm hover:ring-1 hover:ring-gray-900/5{% endif %}">
                    <div class="mr-3 p-1.5 rounded-lg {% if request.resolver_match.url_name == 'dashboard' %}bg-white/20 text-white{% else %}bg-gray-100 text-gray-400 group-hover:bg-brand-50 group-hover:text-brand-600{% endif %} transition-colors">
                        <i data-lucide="layout-dashboard" class="w-4 h-4"></i>
                    </div>
                    Dashboard
                </a>
                <a href="{% url 'system_admin_dashboard' %}?tab=engineers" class="group flex items-center px-4 py-3 mx-2 rounded-xl text-sm font-semibold transition-all duration-300 {% if 'tab=engineers' in request.get_full_path %}bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/30 ring-1 ring-white/20 transform scale-[1.02]{% else %}text-gray-500 hover:text-gray-900 hover:bg-white hover:shadow-sm hover:ring-1 hover:ring-gray-900/5{% endif %}">
                    <div class="mr-3 p-1.5 rounded-lg {% if 'tab=engineers' in request.get_full_path %}bg-white/20 text-white{% else %}bg-gray-100 text-gray-400 group-hover:bg-brand-50 group-hover:text-brand-600{% endif %} transition-colors">
                        <i data-lucide="user-cog" class="w-4 h-4"></i>
                    </div>
                    Engineers
                </a>
                <a href="{% url 'project_list' %}" class="group flex items-center px-4 py-3 mx-2 rounded-xl text-sm font-semibold transition-all duration-300 {% if 'projects' in request.path %}bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/30 ring-1 ring-white/20 transform scale-[1.02]{% else %}text-gray-500 hover:text-gray-900 hover:bg-white hover:shadow-sm hover:ring-1 hover:ring-gray-900/5{% endif %}">
                    <div class="mr-3 p-1.5 rounded-lg {% if 'projects' in request.path %}bg-white/20 text-white{% else %}bg-gray-100 text-gray-400 group-hover:bg-brand-50 group-hover:text-brand-600{% endif %} transition-colors">
                        <i data-lucide="briefcase" class="w-4 h-4"></i>
                    </div>
                    Projects
                </a>
                <a href="{% url 'system_admin_dashboard' %}?tab=teams" class="group flex items-center px-4 py-3 mx-2 rounded-xl text-sm font-semibold transition-all duration-300 {% if 'tab=teams' in request.get_full_path %}bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/30 ring-1 ring-white/20 transform scale-[1.02]{% else %}text-gray-500 hover:text-gray-900 hover:bg-white hover:shadow-sm hover:ring-1 hover:ring-gray-900/5{% endif %}">
                    <div class="mr-3 p-1.5 rounded-lg {% if 'tab=teams' in request.get_full_path %}bg-white/20 text-white{% else %}bg-gray-100 text-gray-400 group-hover:bg-brand-50 group-hover:text-brand-600{% endif %} transition-colors">
                        <i data-lucide="users" class="w-4 h-4"></i>
                    </div>
                    Teams
                </a>
                <a href="{% url 'user_calendar' %}" class="group flex items-center px-4 py-3 mx-2 rounded-xl text-sm font-semibold transition-all duration-300 {% if 'calendar' in request.path %}bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/30 ring-1 ring-white/20 transform scale-[1.02]{% else %}text-gray-500 hover:text-gray-900 hover:bg-white hover:shadow-sm hover:ring-1 hover:ring-gray-900/5{% endif %}">
                    <div class="mr-3 p-1.5 rounded-lg {% if 'calendar' in request.path %}bg-white/20 text-white{% else %}bg-gray-100 text-gray-400 group-hover:bg-brand-50 group-hover:text-brand-600{% endif %} transition-colors">
                        <i data-lucide="calendar" class="w-4 h-4"></i>
                    </div>
                    Calendar
                </a>
                <a href="{% url 'pia_home' %}" class="group flex items-center px-4 py-3 mx-2 rounded-xl text-sm font-semibold transition-all duration-300 {% if 'pia' in request.path %}bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/30 ring-1 ring-white/20 transform scale-[1.02]{% else %}text-gray-500 hover:text-gray-900 hover:bg-white hover:shadow-sm hover:ring-1 hover:ring-gray-900/5{% endif %}">
                    <div class="mr-3 p-1.5 rounded-lg {% if 'pia' in request.path %}bg-white/20 text-white{% else %}bg-gray-100 text-gray-400 group-hover:bg-brand-50 group-hover:text-brand-600{% endif %} transition-colors">
                        <i data-lucide="brain-circuit" class="w-4 h-4"></i>
                    </div>
                    PIA
                </a>
                <a href="{% url 'risks_register' %}" class="group flex items-center px-4 py-3 mx-2 rounded-xl text-sm font-semibold transition-all duration-300 {% if 'risks' in request.path %}bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/30 ring-1 ring-white/20 transform scale-[1.02]{% else %}text-gray-500 hover:text-gray-900 hover:bg-white hover:shadow-sm hover:ring-1 hover:ring-gray-900/5{% endif %}">
                    <div class="mr-3 p-1.5 rounded-lg {% if 'risks' in request.path %}bg-white/20 text-white{% else %}bg-gray-100 text-gray-400 group-hover:bg-brand-50 group-hover:text-brand-600{% endif %} transition-colors">
                        <i data-lucide="shield-alert" class="w-4 h-4"></i>
                    </div>
                    Risks
                </a>
                <a href="{% url 'notes_dashboard' %}" class="group flex items-center px-4 py-3 mx-2 rounded-xl text-sm font-semibold transition-all duration-300 {% if 'notes' in request.path %}bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/30 ring-1 ring-white/20 transform scale-[1.02]{% else %}text-gray-500 hover:text-gray-900 hover:bg-white hover:shadow-sm hover:ring-1 hover:ring-gray-900/5{% endif %}">
                    <div class="mr-3 p-1.5 rounded-lg {% if 'notes' in request.path %}bg-white/20 text-white{% else %}bg-gray-100 text-gray-400 group-hover:bg-brand-50 group-hover:text-brand-600{% endif %} transition-colors">
                        <i data-lucide="file-text" class="w-4 h-4"></i>
                    </div>
                    Notes
                </a>
                {% else %}
                <a href="{% url 'dashboard' %}" class="group flex items-center px-4 py-3 mx-2 rounded-xl text-sm font-semibold transition-all duration-300 {% if request.resolver_match.url_name == 'dashboard' %}bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/30 ring-1 ring-white/20 transform scale-[1.02]{% else %}text-gray-500 hover:text-gray-900 hover:bg-white hover:shadow-sm hover:ring-1 hover:ring-gray-900/5{% endif %}">
                    <div class="mr-3 p-1.5 rounded-lg {% if request.resolver_match.url_name == 'dashboard' %}bg-white/20 text-white{% else %}bg-gray-100 text-gray-400 group-hover:bg-brand-50 group-hover:text-brand-600{% endif %} transition-colors">
                        <i data-lucide="layout-dashboard" class="w-4 h-4"></i>
                    </div>
                    Dashboard
                </a>
                <a href="{% url 'project_list' %}" class="group flex items-center px-4 py-3 mx-2 rounded-xl text-sm font-semibold transition-all duration-300 {% if 'projects' in request.path %}bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/30 ring-1 ring-white/20 transform scale-[1.02]{% else %}text-gray-500 hover:text-gray-900 hover:bg-white hover:shadow-sm hover:ring-1 hover:ring-gray-900/5{% endif %}">
                    <div class="mr-3 p-1.5 rounded-lg {% if 'projects' in request.path %}bg-white/20 text-white{% else %}bg-gray-100 text-gray-400 group-hover:bg-brand-50 group-hover:text-brand-600{% endif %} transition-colors">
                        <i data-lucide="briefcase" class="w-4 h-4"></i>
                    </div>
                    Projects
                </a>
                <a href="{% url 'user_calendar' %}" class="group flex items-center px-4 py-3 mx-2 rounded-xl text-sm font-semibold transition-all duration-300 {% if 'calendar' in request.path %}bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/30 ring-1 ring-white/20 transform scale-[1.02]{% else %}text-gray-500 hover:text-gray-900 hover:bg-white hover:shadow-sm hover:ring-1 hover:ring-gray-900/5{% endif %}">
                    <div class="mr-3 p-1.5 rounded-lg {% if 'calendar' in request.path %}bg-white/20 text-white{% else %}bg-gray-100 text-gray-400 group-hover:bg-brand-50 group-hover:text-brand-600{% endif %} transition-colors">
                        <i data-lucide="calendar" class="w-4 h-4"></i>
                    </div>
                    Calendar
                </a>
                <a href="{% url 'pia_home' %}" class="group flex items-center px-4 py-3 mx-2 rounded-xl text-sm font-semibold transition-all duration-300 {% if 'pia' in request.path %}bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/30 ring-1 ring-white/20 transform scale-[1.02]{% else %}text-gray-500 hover:text-gray-900 hover:bg-white hover:shadow-sm hover:ring-1 hover:ring-gray-900/5{% endif %}">
                    <div class="mr-3 p-1.5 rounded-lg {% if 'pia' in request.path %}bg-white/20 text-white{% else %}bg-gray-100 text-gray-400 group-hover:bg-brand-50 group-hover:text-brand-600{% endif %} transition-colors">
                        <i data-lucide="brain-circuit" class="w-4 h-4"></i>
                    </div>
                    PIA
                </a>
                <a href="{% url 'my_team' %}" class="group flex items-center px-4 py-3 mx-2 rounded-xl text-sm font-semibold transition-all duration-300 {% if 'team' in request.path %}bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/30 ring-1 ring-white/20 transform scale-[1.02]{% else %}text-gray-500 hover:text-gray-900 hover:bg-white hover:shadow-sm hover:ring-1 hover:ring-gray-900/5{% endif %}">
                    <div class="mr-3 p-1.5 rounded-lg {% if 'team' in request.path %}bg-white/20 text-white{% else %}bg-gray-100 text-gray-400 group-hover:bg-brand-50 group-hover:text-brand-600{% endif %} transition-colors">
                        <i data-lucide="users" class="w-4 h-4"></i>
                    </div>
                    Team
                </a>
                <a href="{% url 'issue_tracker' %}" class="group flex items-center px-4 py-3 mx-2 rounded-xl text-sm font-semibold transition-all duration-300 {% if 'issues' in request.path %}bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/30 ring-1 ring-white/20 transform scale-[1.02]{% else %}text-gray-500 hover:text-gray-900 hover:bg-white hover:shadow-sm hover:ring-1 hover:ring-gray-900/5{% endif %}">
                    <div class="mr-3 p-1.5 rounded-lg {% if 'issues' in request.path %}bg-white/20 text-white{% else %}bg-gray-100 text-gray-400 group-hover:bg-brand-50 group-hover:text-brand-600{% endif %} transition-colors">
                        <i data-lucide="bug" class="w-4 h-4"></i>
                    </div>
                    Issues
                </a>
                <a href="{% url 'risks_register' %}" class="group flex items-center px-4 py-3 mx-2 rounded-xl text-sm font-semibold transition-all duration-300 {% if 'risks' in request.path %}bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/30 ring-1 ring-white/20 transform scale-[1.02]{% else %}text-gray-500 hover:text-gray-900 hover:bg-white hover:shadow-sm hover:ring-1 hover:ring-gray-900/5{% endif %}">
                    <div class="mr-3 p-1.5 rounded-lg {% if 'risks' in request.path %}bg-white/20 text-white{% else %}bg-gray-100 text-gray-400 group-hover:bg-brand-50 group-hover:text-brand-600{% endif %} transition-colors">
                        <i data-lucide="shield-alert" class="w-4 h-4"></i>
                    </div>
                    Risks
                </a>
                <a href="{% url 'notes_dashboard' %}" class="group flex items-center px-4 py-3 mx-2 rounded-xl text-sm font-semibold transition-all duration-300 {% if 'notes' in request.path %}bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/30 ring-1 ring-white/20 transform scale-[1.02]{% else %}text-gray-500 hover:text-gray-900 hover:bg-white hover:shadow-sm hover:ring-1 hover:ring-gray-900/5{% endif %}">
                    <div class="mr-3 p-1.5 rounded-lg {% if 'notes' in request.path %}bg-white/20 text-white{% else %}bg-gray-100 text-gray-400 group-hover:bg-brand-50 group-hover:text-brand-600{% endif %} transition-colors">
                        <i data-lucide="file-text" class="w-4 h-4"></i>
                    </div>
                    Notes
                </a>
                {% endif %}
            </nav>"""

new_content = nav_pattern.sub(new_nav, content)

with open('templates/base.html', 'w') as f:
    f.write(new_content)

print("Nav successfully replaced.")
